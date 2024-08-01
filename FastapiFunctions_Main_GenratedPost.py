
from Packages import *


# Set environment variables early
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Firebase app 
load_dotenv()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "sjmain.json"
cred = credentials.Certificate("sjmain.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'sjmain-32689.apppot.com'
    })


# Initialize Bigquery Client
def initialize_bigquery_client():
    load_dotenv()
    source_table_id = os.environ.get("PROJECT_NAME")
    return bigquery.Client(project=source_table_id)

# Remove Unwanted data
def clean_text(text):
    # Remove quotes and leading/trailing whitespace
    text = text.strip().strip('"')
    text = text.strip('[]')
    text = text.strip("```json")
    text = text.strip("```")
    text = text.rstrip(',')
    text = text.rstrip('#')
    return text.strip()


# Genrate image with vertex ai model
def generate_image(prompt_texts: list):
    base_64_strings = []
    image_urls = []
    for prompt_text in prompt_texts:
        base_64_string = None
        while not base_64_string:
            base_64_string = generate_image_base64(prompt_text)
            if not base_64_string:
                prompt_text = ' '.join(prompt_text.split(' ')[:-2])
                if not prompt_text:
                    raise ValueError("Image generation failed after multiple attempts.")
        image_urls.append(save_to_firebase(f'generated_images/{str(uuid.uuid4())}.png', base_64_string, 'image/png'))
    return image_urls

def generate_image_base64(prompt_text: str):
    location = 'location'
    project_id = "project_id"
    vertexai.init(project=project_id, location=location)
    model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    images = []
    while not images:
        try:
            # logger.info(f"Generating image for: {prompt_text}")
            images = model.generate_images(
                prompt=prompt_text,
                number_of_images=1,
                language="en",
                aspect_ratio="1:1",
                safety_filter_level="block_few",
                person_generation="allow_adult",
            )
            if not images:
                logger.warning(f"No images generated for prompt: {prompt_text}")
                prompt_text = ' '.join(prompt_text.split(' ')[:-2])
        except GoogleAPICallError as exp:
            logger.error(f"Error while generating the image: {exp}")
            prompt_text = ' '.join(prompt_text.split(' ')[:-2])
    if images:
        return images[0]._as_base64_string()
    else:
        logger.error(f"Failed to generate image for prompt: {prompt_text}")
        return None

# save image in firebase
def save_to_firebase(blob_file_path: str, base_64_string: str, content_type: str='image/png') -> str:
    decoded_file = base64.b64decode(base_64_string)
    bucket = fb_storage.bucket()
    blob = bucket.blob(blob_file_path)
    blob.upload_from_string(decoded_file, content_type=content_type)
    blob.make_public()
    logger.info("Uploaded to Firebase with URL: {}".format(blob.public_url))
    return blob.public_url


# save data in bigquery
def save_to_bigquery(schedule):
    project_id = 'project_id'
    dataset_id = 'dataset_id'
    table_id = 'table_id'

    client = bigquery.Client(project=project_id)
    table_ref = client.dataset(dataset_id).table(table_id)
    
    rows_to_insert = [
        {
            "client_id": post["client_id"],
            "post_image_horizontal": ",".join(post["post_image_horizontal"]) if "post_image_horizontal" in post else "",
            'post_content':",".join(post["post_content"]) if "post_content" in post else "",
            "post_title": ",".join(post["post_title"]) if "post_title" in post else "",
            "hashtags": ",".join(post["hashtags"]) if "hashtags" in post else "",
            "post_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          
            # Add other fields as needed
        }
        for post in schedule
    ]

    if rows_to_insert:
        errors = client.insert_rows_json(table_ref, rows_to_insert)
        if not errors:
            logger.info("New rows have been added to BigQuery.")
        else:
            logger.error(f"Encountered errors while inserting rows: {errors}")
    else:
        logger.error("No rows to insert into BigQuery.")



# Extracted image text
def extract_image_prompts(generated_description):
    try:
        parsed_json = json.loads(generated_description)
        image_prompts = []
        for post in parsed_json.values():
            if isinstance(post, dict) and 'image' in post:
                image_prompts.append(post['image'])
        
        return image_prompts
    except json.JSONDecodeError:
        prompt_template_image = '''
        You are a text extraction bot. Extract all the texts for the 'Image' parameter from this content:

        {Generated_Description}

        NOTE: Just preprocess and extract the texts for 'Image'. Return the extracted texts as a JSON array of strings.
        '''
        Image_prompt = prompt_template_image.format(Generated_Description=generated_description)
        generative_multimodal_model = GenerativeModel("gemini-1.5-flash-001")
        response_image = generative_multimodal_model.generate_content([Image_prompt])
        
        extracted_image_texts = response_image.text.split('\n')
        
        # Filter out empty strings, brackets, and clean the texts
        cleaned_texts = [clean_text(text) for text in extracted_image_texts if text.strip() and text.strip() not in ['[', ']']]
        
        return cleaned_texts


# Extracted  content text from post
def extract_content_prompts(generated_description: str) -> List[str]:
    try:
        parsed_json = json.loads(generated_description)
        # Extract all content descriptions from the parsed JSON
        content_prompts = []
        for post in parsed_json.values():
            if isinstance(post, dict) and 'Content' in post:
                content_prompts.append(post['Content'])
        
        return content_prompts
    except json.JSONDecodeError:
        prompt_template_content = '''
        You are a text extraction bot. Extract all the texts for the 'Content' parameter from this content:

        {Generated_Description}

        NOTE: Just preprocess and extract the texts for 'Content'. Return the extracted texts as a JSON array of strings.
        '''
        Content_prompt = prompt_template_content.format(Generated_Description=generated_description)
        generative_multimodal_model = GenerativeModel("gemini-1.5-flash-001")
        response_content = generative_multimodal_model.generate_content([Content_prompt])
        
        extracted_content_texts = response_content.text.split('\n')
        cleaned_texts = [clean_text(text) for text in extracted_content_texts if text.strip() and text.strip() not in ['[', ']']]
        
        return cleaned_texts


# Extracted headlines text
def extract_headline_prompts(generated_description: str) -> List[str]:
    try:
        parsed_json = json.loads(generated_description)
        # Extract all headline descriptions from the parsed JSON
        headline_prompts = []
        for key, post in parsed_json.items():
            if isinstance(post, dict) and 'Headline' in post:
                headline_prompts.append(post['Headline'])
        
        return headline_prompts
    except json.JSONDecodeError:
        prompt_template_headline = '''
        You are a text extraction bot. Extract all the texts for the 'Headline' parameter from this content:

        {Generated_Description}

        NOTE: Just preprocess and extract the texts for 'Headline'. Return the extracted texts as a JSON array of strings.
        '''
        Headline_prompt = prompt_template_headline.format(Generated_Description=generated_description)
        generative_multimodal_model = GenerativeModel("gemini-1.5-flash-001")
        response_headline = generative_multimodal_model.generate_content([Headline_prompt])
        
        extracted_response_headline_texts = response_headline.text.split('\n')
        cleaned_texts = [clean_text(text) for text in extracted_response_headline_texts if text.strip() and text.strip() not in ['[', ']']]
        return cleaned_texts

 
# Extracted  hashtags text  
def extract_hashtags_prompts(generated_description: str) -> List[str]:
    try:
        parsed_json = json.loads(generated_description)
        # Extract all hashtag descriptions from the parsed JSON
        hashtags_prompts = []
        for key, post in parsed_json.items():
            if isinstance(post, dict) and 'Hashtags' in post:
                hashtags_prompts.append(post['Hashtags'])
        
        return hashtags_prompts
    except json.JSONDecodeError:
        prompt_template_hashtags = '''
        You are a text extraction bot. Extract all the texts for the 'Hashtags' parameter from this content:

        {Generated_Description}

        NOTE: Just preprocess and extract the texts for 'Hashtags'. Return the extracted texts as a JSON array of strings.
        '''
        Hashtags_prompt = prompt_template_hashtags.format(Generated_Description=generated_description)
        generative_multimodal_model = GenerativeModel("gemini-1.5-flash-001")
        response_hashtags = generative_multimodal_model.generate_content([Hashtags_prompt])
        
        extracted_response_hashtags_texts = response_hashtags.text.split('\n')
        cleaned_texts = [clean_text(text) for text in extracted_response_hashtags_texts if text.strip() and text.strip() not in ['[', ']']]
        
        return cleaned_texts
