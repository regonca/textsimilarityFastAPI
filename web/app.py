from fastapi import FastAPI  # Initialize FastAPI app
from pydantic import BaseModel  # Request body models (replace request.get_json())
from pymongo import MongoClient
import bcrypt
import spacy
import uvicorn

app = FastAPI()  # Initialize FastAPI app

client = MongoClient('mongodb://db:27017/') # Connect to MongoDB (service name "db" in docker-compose)
db = client['SimilarityDB']  # Database name
users = db['Users']  # Collection name

class RegisterRequest(BaseModel):  # Expected JSON body for /register
    username: str
    password: str

class DetectRequest(BaseModel):  # Expected JSON body for /detect
    username: str
    password: str
    text1: str
    text2: str

class RefillRequest(BaseModel):  # Expected JSON body for /refill
    username: str
    admin_pw: str
    refill: int

def UserExist(username):  # Function to check if user exists
    if users.find_one({'username': username}):
        return True
    else:
        return False

@app.post('/register')  # Register endpoint
def register(postedData: RegisterRequest):  # Data is parsed and validated from the JSON body
    username = postedData.username
    password = postedData.password

    if UserExist(username):
        return {'status': 301,
                'message': 'Invalid Username'
               }

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())  # Hash the password
    users.insert_one({'username': username,
                       'password': hashed_pw,
                       'Tokens': 6
                     })  # Insert user
    return {'status': 200,
            'message': 'User registered successfully to the API'
           }

def verifyPw(username, password):  # Function to verify password
    hashed_pw = users.find_one({'username': username})['password']  # Get hashed password from DB
    if bcrypt.checkpw(password.encode('utf-8'), hashed_pw):  # Check password
        return True
    else:
        return False

def countTokens(username):  # Function to count user tokens
    tokens = users.find_one({'username': username})['Tokens']
    return tokens

@app.post('/detect')  # Detect endpoint
def detect(postedData: DetectRequest):
    username = postedData.username
    password = postedData.password
    text1 = postedData.text1
    text2 = postedData.text2

    if not UserExist(username):
        return {'status': 301,
                'message': 'Invalid Username'
               }

    hashed_pw = users.find_one({'username': username})['password']  # Get hashed password from DB

    if not bcrypt.checkpw(password.encode('utf-8'), hashed_pw):  # Check password
        return {'status': 302,
                'message': 'Invalid Password'
               }

    num_tokens = countTokens(username)  # Get user tokens

    if num_tokens <= 0:  # Check if user has enough tokens
        return {'status': 303,
                'message': 'Not enough tokens'
               }

    nlp = spacy.load('en_core_web_sm')  # Load spaCy model
    text1_nlp = nlp(text1)  # Process text1
    text2_nlp = nlp(text2)  # Process text2

    # ratio is a float value between 0 and 1, where 1 means the texts are identical and 0 means they are completely different
    ratio = text1_nlp.similarity(text2_nlp)  # Calculate similarity score

    current_tokens = countTokens(username)  # Get current token count

    users.update_one(
        {'username': username},
        {'$set': {'Tokens': current_tokens - 1}
        })  # Deduct one token

    return {'status': 200,
            'similarity_score': ratio,
            'message': 'Similarity score calculated successfully'
           }

@app.post('/refill')  # Refill endpoint
def refill(postedData: RefillRequest):
    username = postedData.username
    password = postedData.admin_pw
    refill_amount = postedData.refill

    if not UserExist(username):
        return {'status': 301,
                'message': 'Invalid Username'
               }

    correct_pw = 'admin123'  # Admin password

    if password != correct_pw:  # Check admin password
        return {'status': 304,
                'message': 'Invalid Admin Password'
               }

    current_tokens = countTokens(username)  # Get current token count

    users.update_one(
        {'username': username},
        {'$set': {'Tokens': current_tokens + refill_amount}
        })  # Refill tokens

    return {'status': 200,
            'message': 'Refilled successfully'
           }

if __name__ == "__main__":  #
    uvicorn.run(app, host='0.0.0.0', port=5000)
