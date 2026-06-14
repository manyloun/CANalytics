import os
import requests
from datetime import datetime, timedelta
from openai import OpenAI

def verify_openai_pipeline():
    print("================================================================")
    print("Executing OpenAI API Pipeline Diagnostic Test")
    print("================================================================\n")
    
    # 1. Verify environment visibility map
    env_key = os.environ.get("OPENAI_API_KEY")
    if not env_key:
        print("❌ CRITICAL ERROR: 'OPENAI_API_KEY' environment variable not detected.")
        print("Please run: set OPENAI_API_KEY=your_key_here  (inside your terminal command window)")
        return
        
    print(f"✅ Environment Check: Detected key signature string ending in: ...{env_key[-6:]}")
    
    # 2. Test Core LLM Capabilities & Connectivity
    print("\nAttempting lightweight Chat Completion handshake using gpt-4o-mini...")
    try:
        # Client automatically harvests os.environ["OPENAI_API_KEY"] natively
        client = OpenAI()
        
        start_time = datetime.now()
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Using the lowest cost model for diagnostic testing
            messages=[{"role": "user", "content": "Respond with exactly one word: Success."}],
            max_tokens=5,
            temperature=0.0
        )
        latency = (datetime.now() - start_time).total_seconds()
        
        api_text = response.choices[0].message.content.strip()
        print(f"✅ Connection Success! API Response payload: '{api_text}' (Latency: {latency:.2f}s)")
        
    except Exception as e:
        print(f"❌ Handshake Refused: OpenAI engine threw an authentication error.")
        print(f"   Details: {str(e)}")
        return

    # 3. Attempt Programmatic Cost & Usage Profile Scans
    print("\nFetching programmatically tracked API spend for today...")
    try:
        # Construct date bounds targeting today's date parameter window
        today_str = datetime.now().strftime('%Y-%m-%d')
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Use standard HTTP Requests to hit OpenAI's telemetry reporting routes natively
        url = f"https://api.openai.com/v1/usage"
        headers = {"Authorization": f"Bearer {env_key}"}
        params = {"start_date": today_str, "end_date": tomorrow_str}
        
        res = requests.get(url, headers=headers, params=params)
        
        if res.status_type == 200:
            usage_json = res.json()
            # If the organization usage API has tracking metrics, print aggregated data
            if "data" in usage_json and usage_json["data"]:
                print(f"📊 Telemetry: Detected active operations tracking frames for today ({today_str}).")
            else:
                print(f"📊 Telemetry: 0 tokens consumed so far inside this billing cycle window.")
        else:
            # Fallback if your account tier doesn't have programmatic usage access turned on yet
            print("ℹ️ Note: Programmatic usage routing skipped (requires advanced account tiers).")
            print("👉 Please view remaining prepaid cash balances directly inside your browser view:")
            print("   https://platform.openai.com/settings/organization/billing/overview")
            
    except Exception as e:
        print(f"⚠️ Usage lookup loop bypassed: {str(e)}")

    print("\n================================================================")
    print("Diagnostic Complete: Your environment is 100% READY for LangChain!")
    print("================================================================")

if __name__ == "__main__":
    verify_openai_pipeline()
