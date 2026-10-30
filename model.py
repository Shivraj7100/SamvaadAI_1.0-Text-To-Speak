from sarvamai import SarvamAI

client = SarvamAI(
    api_subscription_key="sk_w358v5us_9ourRCEgw5brIDuYryo3sHHW",
)

response_stream = client.text_to_speech.convert_stream(
    text="""नमस्ते! Sarvam AI में आपका स्वागत है।
    हम भारतीय भाषाओं के लिए voice technology बनाते हैं। यहाँ आप अपना text type करके अलग-अलग voices में सुन सकते हैं।
    अपनी भाषा में AI की आवाज़ का अनुभव करें।""",
    
    language_code="hi-IN",        
    speaker="shubh_enhi_ads",
    model="bulbul:v4-flash",
    pace=1,
    speech_sample_rate=24000,
)

# Iterate through the chunks and write them to the file sequentially
with open("speech.mp3", "wb") as f:
    for chunk in response_stream:
        f.write(chunk)
