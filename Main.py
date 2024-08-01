from Packages import *
from FastapiFunctions_Main_GenratedPost import *



# Initialize FastAPI
app = FastAPI()

# Genrate Post Image Endpoint
@app.get("/Genrate_Post/")
def get_description(client_ids: list = Query(..., description="List of client IDs"), Post_frequency: int = Query(..., description="Number of posts to generate per client")):
    try:
        palm_api_key = os.environ.get('PALM_API_KEY')
        if not palm_api_key:
            raise ValueError("Palm API key not found in environment variables")

        # Initialize necessary services
        model = ChatGooglePalm(google_api_key=palm_api_key)
        PROJECT_ID = "projectid"
        REGION = "region-nmae"
        vertexai.init(project=PROJECT_ID, location=REGION)

        client = initialize_bigquery_client()
        source_table_id = os.environ.get("source_table_id")

        # Prepare to store all generated posts
        all_posts = []

        for client_id in client_ids:
            query = f"""
            SELECT *
            FROM `{source_table_id}`
            WHERE Client_Id = '{client_id}'
            LIMIT 1
            """
            query_job = client.query(query)
            results = query_job.result()

            if results.total_rows == 0:
                logger.warning(f"No data found for client ID: {client_id}")
                continue

            row = next(results)

            Products = row.get("Products", "No description available")
            Category = row.get("Category", "No description available")
            Web_Summary = row.get("Web_Summary", "No description available")

            # Generate prompt based on retrieved data
            prompt_template = '''
            A knowledgeable blogger will generate fascinating social media material for businesses to increase their profile and drive business. You want me to perform a task:

            I will offer you the company details. Category: {Category}.
            Products: {Products}.
            Web Summary: {Web_Summary}.

            1. Create unique and cutting-edge post material based on business entities details.
            2. Use fascinating language to promote the business in various ways.
            3. Provide {Post_frequency} different content possibilities for each prompt and hashtags also provides.
            4. Create fresh, unique information every time to avoid recurrence.
            5. Content Preferred Tone is Professional.

            Using this information, construct an initial set of {Post_frequency} distinct social media posts. Avoid the subpart item/option suggestions in three times, 
            just single item to the post recommend. Just return {Post_frequency} post. Each post item generates a single option and image content and hashtags also provide.
            This strategy will highlight the flexibility and consistency of the content generation process,
            while also ensuring every item is fresh and aligned with your marketing objectives.
            '''
            prompt = prompt_template.format(Category=Category, Products=Products, Web_Summary=Web_Summary, Post_frequency=Post_frequency)

            # Generate content using a generative model
            generative_multimodal_model = GenerativeModel("gemini-1.5-flash-001")
            response = generative_multimodal_model.generate_content([prompt])
            Generated_Description = response.text

            logger.info(f'Generated_Description for client ID {client_id}: {Generated_Description}')

            # Extract necessary prompts from generated content
            extracted_image_texts = extract_image_prompts(Generated_Description)

            extracted_content_prompts = extract_content_prompts(Generated_Description)
            extracted_content_prompts = [item for item in extracted_content_prompts if item != '']

            extracted_headline_prompts = extract_headline_prompts(Generated_Description)
            extracted_headline_prompts = [item for item in extracted_headline_prompts if item != '']

            extracted_hashtags_prompts = extract_hashtags_prompts(Generated_Description)
            extracted_hashtags_prompts = [item for item in extracted_hashtags_prompts if item != '']

           

            # Generate images, if needed, for each prompt
            image_urls = []
            for prompt in extracted_image_texts:
                if not prompt:
                    continue
                try:
                    urls = generate_image([prompt])
                    image_urls.extend(urls)
                except Exception as e:
                    logger.error(f"Error generating image for prompt '{prompt}': {e}")

            logger.info(f'Image URLs for client ID {client_id}: {image_urls}')

            # Prepare data for saving to BigQuery
            for i in range(Post_frequency):
                post_data = {
                    "client_id": client_id,
                    "post_image_horizontal": [image_urls[i]] if i < len(image_urls) else [],
                    "post_content": [extracted_content_prompts[i]] if i < len(extracted_content_prompts) else [],
                    "post_title": [extracted_headline_prompts[i]] if i < len(extracted_headline_prompts) else [],
                    "hashtags": [extracted_hashtags_prompts[i]] if i < len(extracted_hashtags_prompts) else [],
                    "post_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                all_posts.append(post_data)

        # Save all generated posts to BigQuery or local file
        save_to_bigquery(all_posts)
        df = pd.DataFrame(all_posts)
        df.to_csv('created_posts_data.csv', index=False)

        return {
            "Generated_Posts": all_posts,
        }

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")







