# Apply ME

#### Video Demo: <URL HERE>

#### Description: "Apply ME" is a job organizer that keeps track of how many apps a user applied, the job description, and what status they're on for that specific position.

Apply ME solves the issue of how many apply for hundreds of jobs but fail to record the job description. So when they are about to interview for that position, they don't know how they should present themselves infront of interviewers.

Apply ME has several webpages.

1. Register
   - On the registration page, the user must sign up for an account with a username that does not already exist and a password that is at least 12 characters long and includes 1 numeric character.
   - The registration page checks whether:
     - the username, password, or password confirmation fields are empty
     - the password confirmation does not match the password
     - the username is already in use
     - the password is at least 12 characters long and includes 1 numeric character
   - Otherwise, a Grumpy Cat page will pop up, and the user will have to go back.
2. Login
   - On the login page, the user should enter their username and password to sign in.
   - The login page checks whether:
     - the username or password fields are empty
     - the username and password match
   - Otherwise, a Grumpy Cat page will pop up, and the user will have to go back.
3. Profile/Homepage
   - After logging in, the user will be taken to their profile/homepage.
   - The profile page consists of a profile card that can be updated and a job statuses table that shows how many jobs are currently at what stage.
   - To edit the profile card, click the pencil icon in the upper right-hand corner of the card.
4. Add Jobs
   - To add a job record, click "Add Job" on the navigation bar, which will take the user to a form.
   - Job Title, Company, and Current Status are required fields to fill out before submitting the form with the blue "Add Job" button.
5. Jobs
   - The Jobs page contains all records of all the jobs the user added, as well as querying capabilities.
   - In the "Current Jobs" section, the user's jobs are listed in a table. The user can edit or remove them using the buttons on the right.
     - Clicking a job record expands to show more details.
   - Search functionality includes:
     - Search input bar
       - By default, when the user writes text and clicks the search button, a query will search for that text in the job title, company, industry, salary, city, state, and job site fields.
     - Search by Multiselect dropdown
       - The user can select what fields they want to search in.
     - Filters Dropdown
       - Allows the user to filter based on job type, commute type, status, date created, date posted, and date applied.
       - Toggle the filters dropdown to show or hide by clicking the button.
       - The filters are not live, meaning that after checking off or choosing a date range, the user must click the "Search" button to submit the form.
       - For the date range picker, choose dates from the calendar or type MM/DD/YYYY - MM/DD/YYYY. Date range pickers are inclusive.
     - To submit the search, press the "Search" button.
