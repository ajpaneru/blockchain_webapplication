from flask import Flask, render_template, request, redirect, url_for, session
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from ethairballoons import ethairBalloons
from web3 import Web3
from solcx import set_solc_version


set_solc_version('0.8.28')  # Set Solidity compiler version


web3Provider = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))  # Ganache WebSocket provider
provider = ethairBalloons('127.0.0.1', 'contracts/')  # Keep contract save path intact


survey_schema = provider.createSchema(modelDefinition={
    'name': "SurveyResponse",
    'contractName': "SurveyResponsesContract",
    'properties': [
        {'name': "email", 'type': "bytes32", 'primaryKey': True},
        {'name': "q1", 'type': "uint"},
        {'name': "q2", 'type': "uint"},
        {'name': "q3", 'type': "uint"},
        {'name': "average_score", 'type': "uint"}
    ]
})

# Deploy the contract
try:
    survey_schema.deploy()
    print("Contract deployed successfully!")
except Exception as e:
    print(f"Error deploying contract: {e}")

# Flask setup
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Response scoring
RESPONSE_SCORES = {
    "Yes, always": 5,
    "Most of the time": 4,
    "Sometimes": 3,
    "Rarely": 2,
    "No, never": 1,
    "Strongly agree": 5,
    "Agree": 4,
    "Neutral": 3,
    "Disagree": 2,
    "Strongly disagree": 1,
    "Very diverse": 5,
    "Somewhat diverse": 4,
    "Neutral": 3,
    "Not very diverse": 2,
    "Not diverse at all": 1
}

# Homepage
@app.route("/")
def index():
    return render_template("index.html")

# Send OTP Email using SendGrid
def send_email(email, otp, username):
    message = Mail(
        from_email="rojanpaneru0002@gmail.com",  # Sender email(Sendgrid)
        to_emails=email,
        subject="Your OTP Code",
        plain_text_content=f"Hello {username},\n\nYour OTP is: {otp}\n\nThank you!"
    )
    try:
        sg = SendGridAPIClient("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")  # SendGrid API key
        response = sg.send(message)
        print(f"Email sent: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

# Send OTP Route
@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form["email"]
    username = request.form["username"]
    otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP

    session["otp"] = otp
    session["email"] = email
    session["username"] = username

    send_email(email, otp, username)
    return redirect(url_for("otp"))

# OTP Verification Route
@app.route("/otp", methods=["GET", "POST"])
def otp():
    if request.method == "POST":
        user_otp = request.form["otp"]
        if user_otp == session.get("otp"):
            return redirect(url_for("survey"))
        else:
            return render_template("otp.html", error_message="Invalid OTP. Please try again.", show_resend=True)

    return render_template("otp.html", error_message=None, show_resend=False)

# Survey page route
@app.route("/survey")
def survey():
    return render_template("survey.html")

@app.route('/submit_survey', methods=['POST'])
def submit_survey():
    try:
        responses = request.form
        print("Received responses:", responses)  # Debugging

        # Map responses to numerical scores
        scores = {
            'q1': RESPONSE_SCORES[responses['q1']],
            'q2': RESPONSE_SCORES[responses['q2']],
            'q3': RESPONSE_SCORES[responses['q3']]
        }
        average_score = sum(scores.values()) / len(scores)

        # Prepare data for blockchain
        survey_data = {
            'email': responses['email'],
            'q1': scores['q1'],
            'q2': scores['q2'],
            'q3': scores['q3'],
            'average_score': int(average_score)
        }
        print("Prepared survey data:", survey_data)  # Debugging

        # Save data to blockchain
        save_receipt = survey_schema.save(survey_data)
        print("Blockchain save receipt:", save_receipt)  # Debugging

        if save_receipt:
            return render_template('survey_success.html', average=average_score)
        else:
            raise Exception("Error saving data to blockchain.")
    except KeyError as e:
        return render_template('error.html', message=f"Missing field: {e}")
    except Exception as e:
        print("Error during survey submission:", e)
        return render_template('error.html', message=f"Error submitting survey: {e}")


# View blockchain data
@app.route("/blockchain")
def view_blockchain():
    try:
        all_records = survey_schema.find()
        return render_template("blockchain.html", blockchain=all_records)
    except Exception as e:
        return render_template("error.html", message=f"Error retrieving blockchain data: {e}")

@app.route('/leaderboard')
def leaderboard():
    try:
        # Fetch data from Ethereum blockchain
        records = survey_schema.find()
        print("Blockchain records:", records)  # Debugging

        # Process records into leaderboard format
        leaderboard_data = {}
        for record in records:
            email = record["email"]
            if isinstance(email, bytes):  # Decode if necessary
                email = email.decode('utf-8')
            domain = email.split('@')[-1]

            if domain not in leaderboard_data:
                leaderboard_data[domain] = {
                    "q1_total": 0,
                    "q2_total": 0,
                    "q3_total": 0,
                    "responses": 0
                }
            leaderboard_data[domain]["q1_total"] += record["q1"]
            leaderboard_data[domain]["q2_total"] += record["q2"]
            leaderboard_data[domain]["q3_total"] += record["q3"]
            leaderboard_data[domain]["responses"] += 1

        # Calculate averages for each domain
        leaderboard_list = []
        for domain, stats in leaderboard_data.items():
            responses = stats["responses"]
            q1_avg = stats["q1_total"] / responses
            q2_avg = stats["q2_total"] / responses
            q3_avg = stats["q3_total"] / responses
            overall_avg = (q1_avg + q2_avg + q3_avg) / 3

            leaderboard_list.append({
                "domain": domain,
                "logo": f"https://logo.clearbit.com/{domain}",
                "q1_avg": round(q1_avg, 2),
                "q2_avg": round(q2_avg, 2),
                "q3_avg": round(q3_avg, 2),
                "overall_avg": round(overall_avg, 2),
                "responses": responses
            })

        # Sort leaderboard
        leaderboard_list.sort(key=lambda x: x["overall_avg"], reverse=True)

        return render_template("leaderboard.html", companies=leaderboard_list)
    except Exception as e:
        print("Error generating leaderboard:", e)
        return render_template("error.html", message=f"Error generating leaderboard: {e}")


def find(self):
    if not self.isDeployed:
        raise Exception('Model is not deployed')
    return self.deployedContract.functions.getAllRecords().call()



# Run the Flask app
if __name__ == "__main__":
    app.run(debug=False)
