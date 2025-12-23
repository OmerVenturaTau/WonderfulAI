# Wonderful Pharmacy Agent


## Overview
This is the state-less AI Agent that I was requested to build.
I created different tools i found relevant (using some statistics) upon the requested tasks.
There are evidence and pictures showing different flows (Evaluation section).
I also created a gemini agent just to test which is better in tasks like this.
I tested it with *gemini-2.5-flash* vs *chat-gpt-5*.
Both are pretty good.
Finally I created a statstics page that uses its own DB which is being updated for utilizing the tools better. That helped me create new tools I found are needed to be more efficient in the tool calls and token usage.



## Evaluation Criteria
Attached in the "Evidence" folder are:
 - A plan to evaluate the agent - **THIS IS A PLAN - I did not try to fix all problems (due to time problems)**. I believe you can understand I know how to handle it though :)

-  Different pictures from flows different flow i evaluated. These contain MultiFlow steps (3 and above most of the time).
You can simply test it by talking with the agent and see the different responses and tools used.

I also created different tests (in the backend) to check all the tools functions and whether they work correctly (syntax and logic).


Next steps will be to go over all different purposed tests and enforcing policies using the system prompt and the tools description. I tested randomly picked ones that I found interesting problems and fixed using prompt engeineering, but I believe there are many more to check and solve.


## Tool Documentation
The tools are documneted in the Evidence "Tools Documentation". It contains all the information regarding the different tools and their purpose.


## Setup
Built with **FastAPI** + **OpenAI Chat Completions API**.
To run it - simply use docker build up.
You do need to provide the .env file. I know you dont  upload it to the github (security reasons practice), but the dockers need it for you to run, so simply copy these:


```
#openai or gemini
MODEL_PROVIDER=openai
MODEL_API_KEY=  
MODEL_VERSION=gpt-5
MAX_TOOL_ROUNDS=10

# Database Configuration (PostgreSQL)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=pharmacy
POSTGRES_USER=pharmacy_user
POSTGRES_PASSWORD=pharmacy_pass

# Port Configuration
BACKEND_PORT=8000
FRONTEND_PORT=8080
DB_PORT=5432
```

put all of these in a .env file and simply run:
```bash
docker-compose up --build
```
**Open in browser**:
   - Navigate to http://localhost:8080
   - Start chatting with the wonderful agent!

This setup uses separate containers for:
- **PostgreSQL Database** (port 5432)
- **Backend API** (port 8000)
- **Frontend Nginx** (port 8080)

