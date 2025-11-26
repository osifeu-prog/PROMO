from passlib.context import CryptContext
from hashlib import sha256
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def generate_contract_hash(data: str):
    return sha256((data + os.environ["SECRET_KEY"]).encode()).hexdigest()
