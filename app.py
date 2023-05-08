import os
import mysql.connector
from datetime import datetime
import time
import boto3
import uuid
from flask import Flask, flash, redirect, render_template, request, session,Blueprint
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required
from decouple import config



def has_numbers(inputString):
    return any(char.isdigit() for char in inputString)

#connect to RDS MySQL final_project database
def get_db_connection():
    return mysql.connector.connect(
        host = config('RDS_HOST'),
        user = config('RDS_USER'),
        password = config('RDS_PASSWORD'),
        database = config('RDS_DB_NAME')
    )

# Configure application
app = Flask(__name__)
posts = Blueprint("posts", __name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

FORM_ITEMS = [
    {"name":"title","placeholder":"Job Title"},
    {"name":"company","placeholder":"Company"},
    {"name":"industry","placeholder":"Industry"},
    {"name":"salary","placeholder":"Salary"},
    {"name":"headquarter_city","placeholder":"City"},
    {"name":"headquarter_state","placeholder":"State"},
    {"name":"job_site","placeholder":"Job Board"},
    {"name":"job_link","placeholder":"Job Link"},
    {"name":"job_type","placeholder":"Job Type"},
    {"name":"commute","placeholder":"Commute Type"},
    {"name":"status","placeholder":"Status"},
    {"name":"date_posted","placeholder":"Date Posted"},
    {"name":"date_applied","placeholder":"Date Applied"},
    {"name":"description","placeholder":"Job Description"}
]

COMMUTE = ["Remote","Hybrid","On-Site"]

STATUSES = ["App in Progress","Applied","Interviewing","Rejected","Received Offer","Denied Offer"]

JOB_TYPES = ["Full-Time","Part-Time","Contract","Internship"]

PROFILE_ITEMS = [{"id":"name", "label": "Name"},
{"id":"job_title", "label": "Job Title"},
{"id":"location", "label": "Location"},
{"id":"linkedin_url", "label": "LinkedIn URL"},
{"id":"github_url", "label": "GitHub URL"}
]

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]
    
    db = get_db_connection()
    cursor = db.cursor()

    # Get the job details
    cursor.execute("SELECT status,count(*) as count FROM jobs WHERE user_id=%s group by status", (id,))
    user_statuses =cursor.fetchall()
    status_dict = {status: 0 for status in STATUSES}
    for status, value in user_statuses:
        status_dict[status] = value

    cursor.execute("SELECT name,job_title,location,github_url,linkedin_url FROM users WHERE id=%s", (id,))
    user_profile = cursor.fetchone()
    profile_dict = {item["id"]: value for item, value in zip(PROFILE_ITEMS, user_profile)}

    cursor.execute("SELECT profile_img_url FROM users WHERE id=%s", (id,))
    profile_img_url = cursor.fetchone()

    return render_template("index.html",status_dict=status_dict, statuses=STATUSES, profile_items =PROFILE_ITEMS,profile_dict=profile_dict,profile_img_url=profile_img_url)

@app.route("/search_jobs")
@login_required
def search_jobs():
    user_id = session["user_id"]
    # connect to the database
    db = get_db_connection()
    cursor = db.cursor()
    # Get the search query from the form
    q = request.args.get('q')
    # Build the SQL query based on the selected filters
    sql, args = build_search_query(user_id,q)

    cursor.execute(sql, args)

    jobs = cursor.fetchall()
    db.close()
    return render_template(
        "jobs.html",
        form_items=FORM_ITEMS,
        commute=COMMUTE,
        statuses=STATUSES,
        jobs=jobs,
        job_types=JOB_TYPES
    )

def build_search_query(user_id,q):
    sql = "SELECT * FROM jobs WHERE user_id = %s"
    args = [user_id]
    filters = {
        "job_type": "job_type",
        "status": "status",
        "commute": "commute"
    }
    # Get the search option selected by the user
    search_by = request.args.getlist("search_by")
    #if they put a value in the dropdown

    if search_by:
        search_columns = []
        for item in FORM_ITEMS[:7]:
            if item["name"] in search_by:
                search_columns.append(item["name"])
    #otherwise default to all values
    else:
        search_columns = [item["name"] for item in FORM_ITEMS[:7]]

    # Modify the SQL query to search only in the selected columns
    sql = f"SELECT * FROM jobs WHERE user_id = %s AND lower(CONCAT({','.join(search_columns)})) LIKE %s"

    #if the
    if q == None:
        q = ''
    args += [f'%{q.lower()}%']

    for filter_key, filter_column in filters.items():
        if filter_key in request.args:
            filter_values = request.args.getlist(filter_key)
            placeholders = ",".join(["%s"] * len(filter_values))
            sql += f" AND {filter_column} IN ({placeholders})"
            args += filter_values

    sql, args = add_date_filter(sql, args, "created_date")
    sql, args = add_date_filter(sql, args, "date_applied")
    sql, args = add_date_filter(sql, args, "date_posted")

    return sql, args

def add_date_filter(sql, args, filter_name):
    date_range = request.args.get(filter_name)
    if date_range:
        start_date, end_date = date_range.split(" - ")
        start_date = datetime.strptime(start_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        sql += f" AND {filter_name} IS NOT NULL AND LEFT({filter_name},10) BETWEEN %s AND %s"
        args += [start_date, end_date]
    return sql, args

@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile(): 
    """Add a job"""
    #connect to RDS MySQL final_project database
    db = get_db_connection()
    #set up a cursor to exectute SQL queries
    cursor = db.cursor()

    # define local variables from form data
    name = request.form.get("name")
    job_title = request.form.get("job_title")
    location = request.form.get("location")
    github_url = request.form.get("github_url")
    linkedin_url = request.form.get("linkedin_url")
    user_id = int(session["user_id"])
    
    #get current img_url
    cursor.execute("SELECT profile_img_url FROM users WHERE id=%s", (user_id,))
    profile_img_url = cursor.fetchone()[0]

    # Get the file from the form data
    file = request.files["file"]
    prefix = config('S3_BUCKET_URL')
    
    if file:
        # Check if the file is an allowed file type
        if not allowed_file(file.filename):
            return apology("File is not allowed")
        
         # Generate a unique filename for the user's profile img url if they don't already have one
        if profile_img_url == prefix + 'default.png':
            new_filename = uuid.uuid4().hex + '.' + file.filename.rsplit('.', 1)[1].lower()
        else:
            new_filename = profile_img_url[len(prefix):]
        # Upload the file to S3

        print(new_filename)
        bucket_name = config('S3_BUCKET_NAME')
        s3_resource = boto3.resource("s3", aws_access_key_id=config('S3_ACCESS_KEY'), aws_secret_access_key=config('S3_SECRET_KEY'))
        s3_bucket = s3_resource.Bucket(bucket_name)
        s3_bucket.upload_fileobj(file, new_filename)

    else:
        new_filename = 'default.png'
    
    new_profile_img_url = prefix + new_filename

    # Add the user's entry into the database
    cursor.execute("UPDATE users SET name =%s,job_title=%s,location=%s,github_url=%s,linkedin_url=%s,profile_img_url=%s where id = %s", (name, job_title, location, github_url, linkedin_url,new_profile_img_url,user_id))
    db.commit()
    db.close()

    flash('Profile updated successfully!')

    return redirect("/")

@app.route('/update_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def update_job(job_id):
    """Update an existing job"""
    db = get_db_connection()
    cursor = db.cursor()

    # Get the job details
    cursor.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
    job = cursor.fetchone()

    # If job doesn't exist, return 404 error
    if not job:
        return render_template('404.html'), 404

    # If form submitted with updated job details
    if request.method == 'POST':
        user_id = session["user_id"]
        title = request.form.get("title")
        company = request.form.get("company")
        industry = request.form.get("industry")
        description = request.form.get("description")
        salary = request.form.get("salary")
        commute = request.form.get("commute")
        headquarter_state = request.form.get("headquarter_state")
        headquarter_city = request.form.get("headquarter_city")
        job_site = request.form.get("job_site")
        job_link = request.form.get("job_link")
        status = request.form.get("status")
        date_posted = request.form.get("date_posted")
        date_applied = request.form.get("date_applied")
        job_type = request.form.get("job_type")
        # Get other fields from form as needed

        if not title:
            return apology("must provide a job title")
        elif not company:
            return apology("must provide a company")
        elif not status or status not in STATUSES:
            return apology("must provide a valid status")
        elif commute != '' and commute not in COMMUTE:
            return apology("must provide a valid commute")
        elif job_type != '' and job_type not in JOB_TYPES:
            return apology("must provide a valid job type")

        # Update the job details in the database
        cursor.execute("UPDATE jobs SET title =%s,company=%s,industry=%s,description=%s,salary=%s,commute=%s,headquarter_state=%s,headquarter_city=%s,job_site=%s,job_link=%s,status=%s,date_posted=%s,date_applied=%s,job_type=%s WHERE id=%s and user_id=%s", (title, company, industry, description, salary, commute, headquarter_state, headquarter_city, job_site, job_link, status, date_posted, date_applied,job_type, job_id,user_id))
        db.commit()
        db.close()

        flash('Job updated successfully!')
        return redirect('/jobs')

    # Render the job update form with existing job details
    return render_template('update_job.html', job=job, statuses = STATUSES,commute = COMMUTE,job_types=JOB_TYPES)

@app.route("/jobs")
@login_required
def jobs():
    #connect to RDS MySQL final_project database
    db = get_db_connection()
    
    #set up a cursor to exectute SQL queries
    cursor = db.cursor()
    
    user_id = int(session["user_id"])

    cursor.execute("SELECT * FROM jobs WHERE user_id = %s", (user_id,))
    jobs =cursor.fetchall()

    db.close()
    # render the template with the data
    return render_template("jobs.html", form_items = FORM_ITEMS, commute = COMMUTE,statuses = STATUSES,jobs=jobs,job_types=JOB_TYPES)



@app.route("/remove_job", methods=["POST"])
@login_required
def remove():
    #connect to RDS MySQL final_project database
    db = get_db_connection()
    #set up a cursor to exectute SQL queries
    cursor = db.cursor()

    job_id = int(request.form.get("id"))
    if id:
        cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        db.commit()
    db.close()
    return redirect("/jobs")

@app.route("/add_job", methods=["GET","POST"])
@login_required
def add_job(): 
    if request.method == "POST":
        """Add a job"""
        #connect to RDS MySQL final_project database
        db = get_db_connection()
        #set up a cursor to exectute SQL queries
        cursor = db.cursor()

        # define local variables from form data
        title = request.form.get("title")
        company = request.form.get("company")
        industry = request.form.get("industry")
        description = request.form.get("description")
        salary = request.form.get("salary")
        commute = request.form.get("commute")
        headquarter_state = request.form.get("headquarter_state")
        headquarter_city = request.form.get("headquarter_city")
        job_site = request.form.get("job_site")
        job_link = request.form.get("job_link")
        status = request.form.get("status")
        date_posted = request.form.get("date_posted")
        date_applied = request.form.get("date_applied")
        job_type = request.form.get("job_type")

        if not date_posted:
            date_posted = None
        if not date_applied:
            date_applied = None
        user_id = int(session["user_id"])
        date_created = time.strftime('%Y-%m-%d %H:%M:%S')
        
        if not status or status not in STATUSES:
            return apology("must provide a valid status")
        elif commute != '' and commute not in COMMUTE:
            return apology("must provide a valid status")
        elif job_type != '' and job_type not in JOB_TYPES:
            return apology("must provide a valid job type")
            
        # Add the user's entry into the database
        cursor.execute("INSERT INTO jobs (user_id, title,company,industry,description,salary,commute,headquarter_state,headquarter_city,job_site,job_link,status,date_posted,date_applied,created_date,job_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)", (user_id, title, company, industry, description, salary, commute, headquarter_state, headquarter_city, job_site, job_link, status, date_posted, date_applied, date_created,job_type))
        db.commit()
        #close the db connection
        db.close()
        return redirect("/jobs")
    else:
        return render_template("add_job_form.html",form_items = FORM_ITEMS, commute = COMMUTE,statuses = STATUSES,job_types=JOB_TYPES)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        # db.execute returns a list of rows that match our select query
        cursor.execute("SELECT * FROM users WHERE username = %s", (request.form.get("username"),))
        rows = cursor.fetchall()
        #rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        #close the db connection
        db.close()
        
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()
    
    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    # when form is submitted via POST check for possible errors and insert the new user into the users table
    """Register user"""
    if request.method == "POST":
        #connect to RDS MySQL final_project database
        db = get_db_connection()
        
        #set up a cursor to exectute SQL queries
        cursor = db.cursor()
        
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        cursor.execute("SELECT * FROM users WHERE username = %s", (request.form.get("username"),))
        rows = cursor.fetchall()
        #rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # check for errors
        # username is empty
        if not username:
            return apology("must provide username", 400)
        # username already exists
        elif len(rows) >= 1:
            return apology("username already exists", 400)
        # password is empty
        elif not password:
            return apology("must provide password", 400)
        # password must contain at least one number
        elif not has_numbers(password):
            return apology("must include at least 1 number in your password", 400)
        # password confirmation is empty
        elif len(password) < 12:
            return apology("password must be at least 12 characters long", 400)
        # password confirmation is empty
        elif not confirmation:
            return apology("must confirm password", 400)
        # password doesn't match confirmation
        elif confirmation != password:
            return apology("password must match confirmation", 400)

        # Add the user's entry into the database
        cursor.execute("INSERT INTO users (username, hash,name,job_title,github_url,linkedin_url,profile_img_url) VALUES(%s, %s,%s, %s,%s, %s,%s)", (username,  generate_password_hash(password),'Name','Job Title','https://github.com/','https://www.linkedin.com/','https://s3.us-east-2.amazonaws.com/692313771617-test/default.png'))
        db.commit()
        #db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username,  generate_password_hash(password))

        # log user in
        cursor.execute("SELECT * FROM users WHERE username = %s", (request.form.get("username"),))
        rows = cursor.fetchall()
        #rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = rows[0][0]

        #close the db connection
        db.close()
        
        return redirect("/")
    else:
        # when requested GET, display registration form
        return render_template("registration.html")


