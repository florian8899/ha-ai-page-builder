import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:4200",
    ]

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Create an instance of the FastAPI application
app = FastAPI(title="Content-Generator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow requests from specified origins
    allow_credentials=True,  # Allow cookies to be included in cross-origin requests
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Define the schema for the expected input using Pydantic
class InputData(BaseModel):
    input: str

# Define a POST endpoint that accepts the JSON object
@app.post("/generate-content", tags=["Data Submission"])
def submit_data(data: InputData):
    response = client.responses.create(
        model="gpt-5",
        instructions='Use the input as a description for a website with one hero section and one feature section containing three features. Generate a title and a subtitle for the hero section and a title for the feature section. Also, generate titles and descriptions for each of the three features. Return the response in the following JSON format where null should be replaced by your generated content: "{\"hero\":{\"title\":null,\"subtitle\":null},\"features\":{\"title\":null,\"feature1\":{\"title\":null,\"description\":null},\"feature2\":{\"title\":null,\"description\":null},\"feature3\":{\"title\":null,\"description\":null}}}"',
        input=data.input,
    )
    return response.output_text
