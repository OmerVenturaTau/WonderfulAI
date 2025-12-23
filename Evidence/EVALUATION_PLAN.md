# Evaluation Plan for Wonderful Pharmacy Agent

## Overview
This is the AI Agent that I was requested to build.
I created different tools i found relevant (using some statistics) upon the requested tasks.
There are evidence and pictures showing different flows (Evaluation section).
I also created a gemini agent just to test which is better in tasks like this.
I tested it with *gemini-2.5-flash* vs *chat-gpt-5*.
Both are pretty good.



## Setup
To run it - simply use docker build up.
You do need to provide the .env file. I did not upload it to the github (security reasons practice), but the dockers need it.
Attached here are the relevant parameters:


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



## Evaluation Criteria
Attached in the "Evidence" folder are different picture from flows.
You can simply test it by talking with the agent and see the different response and tools.
I also created different tests (in the backend) to check all the tools functions and whether they work correctly (syntax and logic)
Next steps will be to go over all different tests and enforcing policies using the system prompt and the tools description, but basically that is the following steps.
