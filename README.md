# 📧 Email Automation Processor  
**Automate email management with Gmail API + PostgreSQL**  
*Process emails using custom rules for filtering and actions*

---

## 🌟 Features  
- ✅ **Gmail Integration** - Secure OAuth2 authentication  
- 🛠 **Custom Rules Engine** - JSON-based configuration  
- 🗄 **PostgreSQL Storage** - Docker container support  
- ⚡ **Automated Actions** - Mark read/unread, label organization  

---

## 🚀 Quick Start  

### 1. Prerequisites  
- Python 3.8+  
- Docker Desktop  
- Google Account  

### 2. Clone & Setup  
- git clone https://github.com/yourusername/automation_email_processor.git
- cd automation_email_processor
- python -m venv venv
- source venv/bin/activate  # Linux/Mac
- venv\Scripts\activate  # Windows
- pip install -r requirements.txt

### Configuring the Gmail API
- If you already have a client_secret.json file, you can skip this section. Otherwise, follow these steps:
- Go to the Google Cloud Console and make sure you're logged into the correct account.
- Create or Select a Project if you don't already have one.
- Navigate to APIs & Services → Library, search for "Gmail API," and Enable it.
- Go to APIs & Services → Credentials.
- Click Create Credentials → OAuth client ID.
- Select Application type = Desktop app (or Web application if that suits your usage).
- Give it a name (e.g., "MyGmailDesktopApp") and click Create.
- Download the OAuth client file, rename it to client_secret.json and place it into the client_secret directory of the repository.

### Database Setup
- You can use the provided Docker setup for PostgreSQL:
1. Ensure you have Docker and Docker Compose installed.
2. From the project root directory, run:  docker-compose up -d
This will spin up a Postgres container with the configuration specified in the docker-compose.yml file.
3. Update your database connection details in the project .env file.


### How to run 
1. Configure Rules
Before running scripts, update the rules/rules.json file to define how emails should be processed. (See Customizing Rules below.)

2. Run the Main Script
          run : python main.py
- This script will authenticate with Gmail (the first time you run it, you'll be prompted to log in) and then parse and store your emails into the database.

3. Process Rules
           run : python process_rules.py
- This script will read the emails from the database and apply your defined rules to perform any specified actions.


### Customizing Rules
- The rules/rules.json file allows you to define conditions for processing your emails. Here's an example of what a single rule might look like:

{
  "rules": [
    {
      "name": "Move Support Emails",
      "condition": {
        "field": "subject",
        "contains": "Support"
      },
      "action": {
        "type": "move",
        "destination": "SupportFolder"
      }
    }
  ]
}


You can define any number of rules. Each rule has:

A name to identify the rule.

A condition (e.g., checking if a certain field contains a keyword).

An action dict specifying what to do when the condition is met.