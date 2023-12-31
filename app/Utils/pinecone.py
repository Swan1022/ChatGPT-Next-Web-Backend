from langchain.schema import Document
import pandas as pd
from fastapi import UploadFile, File
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import CSVLoader, PyPDFLoader, TextLoader, Docx2txtLoader
from app.Utils.web_scraping import extract_content_from_url
from app.Models.ChatbotModel import Chatbot, RequestPayload
from app.Models.ChatLogModel import Message, add_new_message as add_new_message_to_db
from typing import List
import nltk

from dotenv import load_dotenv
import os
import pinecone
import openai
import tiktoken
import time
# from pinecone import Index

load_dotenv()
tokenizer = tiktoken.get_encoding('cl100k_base')

api_key = os.getenv('PINECONE_API_KEY')

pinecone.init(
    api_key=api_key,  # find at app.pinecone.io
    environment=os.getenv('PINECONE_ENV'),  # next to api key in console
)

index_name = os.getenv('PINECONE_INDEX')
embeddings = OpenAIEmbeddings()
similarity_min_value = 0.5
default_prompt = """
    You will act as a legal science expert.
    Please research this context deeply answer questions based on  given context as well as your knowledge.
    If you can't find accurate answer, please reply similar answer to this question or you can give related information to given questions.
    The more you can, the more you shouldn't say you don't know or this context doesn't contain accurate answer.
    If only there is never answer related to question, kindly reply you don't know exact answer.
    Don't output too many answers.
    Below is context you can refer to.
"""
prompt = default_prompt
context = ""


def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)


def delete_all_data():
    # Initialize Pinecone client
    pinecone.init(api_key=api_key, environment=os.getenv('PINECONE_ENV'))

    # # Retrieve the index
    # index = pinecone.Index(index_name="your_index_name")

    # # Delete all data from the index
    # index.delete_index()

    # # Disconnect from Pinecone
    # pinecone.init()
    # pinecone.delete_index("example-index")
    # print(pinecone.list_indexes())
    if index_name in pinecone.list_indexes():
        # Delete the index
        pinecone.delete_index(index_name)
        print("Index successfully deleted.")
    else:
        print("Index not found.")

    pinecone.create_index(
        index_name,
        dimension=1536,
        metric='cosine',
        pods=1,
        replicas=1,
        pod_type='p1.x1'
    )
    print("new: ", pinecone.list_indexes())


def split_document(doc: Document):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=20,
        length_function=tiktoken_len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents([doc])
    return chunks


def train_csv(filename: str, namespace: str):
    start_time = time.time()
    loader = CSVLoader(file_path=f"./train-data/{namespace}-{filename}")
    data = loader.load()
    total_content = ""
    for d in data:
        total_content += "\n\n" + d.page_content
    doc = Document(page_content=total_content, metadata={"source": filename})
    chunks = split_document(doc)
    Pinecone.from_documents(
        chunks, embeddings, p=index_name, namespace=namespace)

    end_time = time.time()
    print("Elapsed time: ", end_time - start_time)
    return True


def train_pdf(filename: str, namespace: str):
    print("begin train_pdf")
    start_time = time.time()
    loader = PyPDFLoader(file_path=f"./train-data/{namespace}-{filename}")
    documents = loader.load()
    # chunks = split_document(documents)
    # print(type(documents))
    total_content = ""
    for document in documents:
        total_content += "\n\n" + document.page_content
    doc = Document(page_content=total_content, metadata={"source": filename})
    chunks = split_document(doc)
    print("chunks: ", chunks)
    Pinecone.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=index_name,
        namespace=namespace
    )
    print("train_namesapce", namespace)
    print("end pdf-loading")
    end_time = time.time()
    print("Elapsed time: ", end_time - start_time)
    return True


def train_txt(filename: str, namespace: str):
    start_time = time.time()
    loader = TextLoader(file_path=f"./train-data/{namespace}-{filename}")
    documents = loader.load()
    total_content = ""
    for document in documents:
        total_content += "\n\n" + document.page_content
    doc = Document(page_content=total_content, metadata={"source": filename})
    print(filename)
    chunks = split_document(doc)
    print("namespace: ", namespace)
    Pinecone.from_documents(
        chunks, embeddings, index_name=index_name, namespace=namespace)
    end_time = time.time()
    print("Elapsed time: ", end_time - start_time)
    return True


def train_ms_word(filename: str, namespace: str):
    start_time = time.time()
    loader = Docx2txtLoader(file_path=f"./train-data/{namespace}-{filename}")
    documents = loader.load()
    chunks = split_document(documents[0])
    print(chunks)
    Pinecone.from_documents(
        chunks, embeddings, index_name=index_name, namespace=namespace)
    end_time = time.time()
    print("Elapsed time: ", end_time - start_time)


# def train_text():
#     print("train-begin")
#     with open("./data/data.txt", "r") as file:
#         content = file.read()
#     doc = Document(page_content=content, metadata={"source": "data1.txt"})
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=1500,
#         chunk_overlap=100,
#         length_function=tiktoken_len,
#         separators=["\n\n", "\n", " ", ""]
#     )
#     chunks = text_splitter.split_documents([doc])

#     Pinecone.from_documents(
#         chunks, embeddings, index_name=index_name)
#     print("train-end")


def train_url(url: str, namespace: str):
    content = extract_content_from_url(url)
    doc = Document(page_content=content, metadata={"source": url})
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=20,
        length_function=tiktoken_len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents([doc])
    Pinecone.from_documents(
        chunks, embeddings, index_name=index_name, namespace=namespace)


def set_prompt(new_prompt: str):
    global prompt
    prompt = new_prompt


def get_context(msg: str, namespace: str):
    print("message" + msg)
    matching_metadata = []
    similarity_value_limit = 0.76
    results = tuple()
# if current_bot.contextBehavior != "gpt":
    print("here")
    db = Pinecone.from_existing_index(
        index_name=index_name, namespace=namespace, embedding=embeddings)
    print("search_namesapce", namespace)
    results = db.similarity_search_with_score(msg, k=1)
    for result in results:
        # print("embedding_id: ", result.metadata['source'])
        if result[1] >= similarity_value_limit:
            matching_metadata.append(result[0].metadata['source'])
    matching_metadata = list(set(matching_metadata))
    # web_db = Pinecone.from_existing_index(
    #     index_name=index_name, embedding=embeddings)
    # web_results = web_db.similarity_search(msg, k=2)
    global context
    context = ""
    # for web_result in web_results:
    #     context += f"\n\n{web_result.page_content}"
    tokens = 0
    for result in results:
        print(result)
        if result[1] >= similarity_value_limit:
            context += f"\n\n{result[0].page_content}"

            tokens += len(nltk.word_tokenize(result[0].page_content))

    print("token: ", tokens)
    # print(context)
    # print("sourceDiscloser: ", current_bot.sourceDiscloser)
    # if current_bot.sourceDiscloser == False:
    #     matching_metadata = []
    return {"context": context, "metadata": matching_metadata}


def get_answer(request_payload: RequestPayload, email: str):
    global context
    global prompt

    # contextBehavior = """You shouldn't answer with your own knowledge.
    #     You should answer only based on the context given below.
    #     Even if you can't find similar answer in the context given, you shouldn't answer with your knowledge.
    # """

    # contextBehavior = contextBehavior if current_bot.contextBehavior == "file" else ""

#         You should answer all questions in {current_bot.language} as long as not mentioned in below prompt.
#         And your tone should be {current_bot.tone} and your writing format should be {current_bot.format} and your writing style should be {current_bot.style}.
#         Your answer should contains at most {current_bot.length} words as possible as you can.
#         Don't output answer of more than {current_bot.length} of words.

#         You will act as mentioned below.
#         {current_bot.behaviorPrompt}

#         {contextBehavior}

#         You should remember that this prompt below is most important instructor and the priority of this give prompt below should be given to the top.
#         This is the give prompt. If any content in the prompt does not match the above mentioned instructions, you should follow the prompt below.

    instructor = f"""
        
        {prompt}
        -----------------------
        {context}
    """
    final = ""
    try:
        response = openai.ChatCompletion.create(
            model=request_payload.model,
            max_tokens=2000,
            messages=[
                {'role': 'system', 'content': instructor},
                request_payload.messages[-1]
            ],
            temperature=request_payload.temperature,
            stream=True
        )
        for chunk in response:
            if 'content' in chunk.choices[0].delta:
                string = chunk.choices[0].delta.content
                # print("string: ", string)
                yield string
                final += string
    except Exception as e:
        print(e)
    print("content :", request_payload.messages[-1]['content'])
    add_new_message_to_db(logId=request_payload.log_Id, botId=request_payload.bot_Id,
                          msg=Message(content=request_payload.messages[-1]['content'], role="user"), email=email)
    add_new_message_to_db(logId=request_payload.log_Id, botId=request_payload.bot_Id,
                          msg=Message(content=final, role="assistant"), email=email)

    # print(response)
    # print(response.choices[0].message.content)


def delete_data_by_metadata(filename: str, namespace: str):

    index = pinecone.Index(index_name=index_name)
    query_response = index.delete(
        namespace=namespace,
        filter={
            "source": filename
        }
    )
    print(query_response)


def get_post_content(text: str):
    instructor = f"""
        This context is the content of one site.
        {text}
        You have to analyze above context and then have to create Instagram post for above context.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            max_tokens=2000,
            messages=[
                {'role': 'system', 'content': instructor},
                {'role': 'user', "content": "Please provide me created Instagram post using above context."}
            ],
        )
        return response.choices[0].message["content"]
    except Exception as e:
        print(e)
