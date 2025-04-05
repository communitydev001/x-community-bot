# main.py - Your main bot script

import tweepy
import os
import json
from datetime import datetime
from topic_analysis import analyze_trending_topics, create_summary

def run_twitter_bot():
    """Main function to run the Twitter bot"""
    
    # Load environment variables (set in GitHub secrets)
    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    consumer_key = os.environ.get("TWITTER_API_KEY")
    consumer_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_SECRET")
    
    # Configure read-only client (for collecting data)
    read_client = tweepy.Client(
        bearer_token=bearer_token
    )
    
    # Configure read-write client (for posting)
    write_client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    # 1. Collect Data
    print("Collecting community tweets...")
    
    # Define your community search terms
    search_query = "(#YourCommunity OR #Topic1 OR #Topic2) -is:retweet"
    
    # Collect tweets (free tier allows 100 per request)
    tweets = read_client.search_recent_tweets(
        query=search_query,
        max_results=100,
        tweet_fields=["created_at", "public_metrics", "entities"]
    )
    
    if not tweets.data:
        print("No tweets found. Exiting.")
        return
    
    tweet_count = len(tweets.data)
    print(f"Collected {tweet_count} tweets")
    
    # 2. Analyze Topics
    print("Analyzing trending topics...")
    analysis_results = analyze_trending_topics(tweets)
    
    # 3. Create Summary
    print("Creating summary...")
    summary = create_summary(analysis_results, tweet_count)
    print("\nSummary Preview:")
    print("-------------------")
    print(summary)
    print("-------------------")
    
    # 4. Post to Twitter
    try:
        print("Posting to Twitter...")
        response = write_client.create_tweet(text=summary)
        print(f"Successfully posted tweet! ID: {response.data['id']}")
    except Exception as e:
        print(f"Error posting to Twitter: {e}")
    
    # 5. Save results to GitHub repo for historical tracking
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Save daily results
        with open(f"results/daily_{today}.json", "w") as f:
            # Don't save full tweet data to avoid storage limits
            json.dump({
                "date": today,
                "tweet_count": tweet_count,
                "top_hashtags": analysis_results["hashtags"],
                "top_phrases": analysis_results["phrases"],
                "summary": summary
            }, f, indent=2)
        
        print("Results saved to repository")
    except Exception as e:
        print(f"Error saving results: {e}")

if __name__ == "__main__":
    run_twitter_bot()
