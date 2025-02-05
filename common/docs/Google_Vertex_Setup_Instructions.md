1. https://console.cloud.google.com/
2. Create Google account
3. Add payment info etc to activate free trial and credits
4. On dashboard, click on Enable Recommended APIs
5. Click top left corner hamburger menu, select APIs & Services -> Credentials, Click on the srevice account
6. Top KEYS -> ADD KEY -> Create new key, keep JSON checked, -> CREATE
7. Key will be saved to downloads. Move it to jaysgame\common\scripts\gemini.key
8. In common\scripts run python python convert_gemini_key_to_encoded_env_variable.py
9. Copy content of gemini_key_encoded.txt to GOOGLE_GEMINI_KEY in .env
10. In .env update GOOGLE_GEMINI_PROJECT_ID to new project ID (available in gemini.key or by clicking on My First Project at top of Vertex page)
11. Don't forget to back up changes to .env!
12. Go to https://console.cloud.google.com/apis/library, search for AI platform, select AI Platform Training & Prediction API, click enable.
13. In top right of Vertex page, click Activate

Test with common\scripts\test_google_with_encoded_env_var.bat

- If not done already, in right env: pip3 install google-cloud-aiplatform
