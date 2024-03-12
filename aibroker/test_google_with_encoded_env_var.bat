for /F %%g in (..\common\gemini.key) do set GOOGLE_GEMINI_KEY=%%g
python test_google_with_encoded_env_var.py
