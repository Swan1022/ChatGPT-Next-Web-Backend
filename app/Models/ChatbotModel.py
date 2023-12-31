from pydantic import BaseModel
from app.Database import db
from typing import List
from bson import json_util
from bson.objectid import ObjectId
from fastapi import Form
ChatbotsDB = db.chatbots


class ChatBotIdModel(BaseModel):
    id: str
    log_id: str


class AddNewBotModel(BaseModel):
    name: str = ""
    description: str = ""
    welcomeMessage: str = "Hello friend! How can I help you today?"
    model: str = "gpt-4"
    language: str = "English"
    tone: str = "Friendly"
    format: str = "FAQ"
    style: str = "Friendly"
    length: str = "50 words"
    password: str = ""
    contextBehavior: str = ""
    behaviorPrompt: str = ""
    fighterPrompt: str = ""
    appendedPrompt: str = ""
    creativity: float = 0.3
    conversationSaver: bool = False
    lastChatLogId: str = ""
    sourceDiscloser: bool = False
    HTMLInterpreter: bool = False


class Chatbot(AddNewBotModel):
    email: str = ""
    pages: List = []
    files: List = []
    messages: List = []


class AskQuestionModel(BaseModel):
    usermsg: str
    id: str
    chatlogId: str


class RequestPayload(BaseModel):
    messages: List = []
    stream: bool
    model: str
    temperature: float
    presence_penalty: float
    frequency_penalty: float
    top_p: float
    bot_Id: str = ""
    log_Id: str = ""


class UserForClient(BaseModel):
    username: str
    email: str


class User(UserForClient):
    hashed_password: str


def add_new_chatbot(email: str, botmodel: AddNewBotModel):
    new_chatbot = Chatbot(email=email, pages=[], files=[], **botmodel.dict())
    # print(new_chatbot.name, new_chatbot.description, new_chatbot.language)
    result = ChatbotsDB.insert_one(new_chatbot.dict())
    return str(result.inserted_id)


def add_page(id: str, url: str):
    print("_id: ", ObjectId(id))
    ChatbotsDB.update_one({"_id": ObjectId(id)}, {"$push": {"pages": url}})
    return True


def remove_page(id: str, url: str):
    print("id: ", url)
    ChatbotsDB.update_one({"_id": ObjectId(id)}, {"$pull": {"pages": url}})
    return True


def add_file(id: str, filename: str):
    print("id: ", id)
    print("filename: ", filename)
    ChatbotsDB.update_one({"_id": ObjectId(id)}, {
                          "$push": {"files": filename}})
    return True


def remove_file(id: str, filename: str):
    ChatbotsDB.update_one({"_id": ObjectId(id)}, {
                          "$pull": {"files": filename}})
    return True


def find_chatbot_by_id(id: str):
    result = ChatbotsDB.find_one({"_id": ObjectId(id)})
    print("result", result)
    return Chatbot(**result)


def update_chatbot_by_id(id: str, log_id: str):
    ChatbotsDB.update_one({"_id": ObjectId(id)}, {
                          "$set": {"lastChatLogId": log_id}})


def find_all_chatbots(email: str):
    result = ChatbotsDB.find({"email": email})
    all_bots = []
    for bot in result:
        bot["_id"] = str(bot["_id"])
        all_bots.append(bot)
    for bot in all_bots:
        print(bot)
    return all_bots


def remove_chatbot(id: str, email: str):
    ChatbotsDB.delete_one({"_id": ObjectId(id), "email": email})
    return True
