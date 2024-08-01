
import json
import os
import uuid
import base64
import re
import logging
from datetime import datetime
import pandas as pd
import vertexai
from fastapi import FastAPI, HTTPException, Query
from typing import List
from dotenv import load_dotenv
from vertexai.preview.vision_models import ImageGenerationModel
import firebase_admin
from firebase_admin import credentials, storage as fb_storage
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPICallError
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatGooglePalm
import google.generativeai as genai
from vertexai.preview.generative_models import GenerativeModel
# from langchain.output_parsers import PydanticOutputParser
# from langchain_core.pydantic_v1 import BaseModel, Field, validator
from pydantic import BaseModel
from langchain import LLMChain
from langchain.chains import SequentialChain
# from langchain.llms import OpenAI
from datetime import date
from FastapiFunctions_Main_GenratedPost import *