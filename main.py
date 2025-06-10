from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import logging
import time
import hashlib
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from agents import create_agent
from tools import available_tools

load_dotenv()
logging.basicConfig(filename='agent_builder.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

scheduler = BackgroundScheduler()
scheduler.start()
logger.info("APScheduler started successfully")

agents = {}
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.errorhandler(405)
def method_not_allowed(e):
    logger.error(f"405 Method Not Allowed: {request.method} on {request.path}")
    return jsonify({'error': f"Method {request.method} not allowed on {request.path}. Use POST."}), 405

@app.after_request
def log_response_headers(response):
    if request.method == "OPTIONS":
        logger.info(f"OPTIONS response headers: {response.headers}")
    return response

class PDFHandler(FileSystemEventHandler):
    def __init__(self, agent_id):
        self.agent_id = agent_id

    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        logger.info(f"New PDF detected: {event.src_path}")
        try:
            time.sleep(1)
            agent_data = agents.get(self.agent_id)
            if not agent_data:
                logger.error(f"Agent {self.agent_id} not found for PDF processing")
                return
            agent = agent_data['agent']
            prompt = f"Summarize the PDF at {event.src_path}"
            output = agent.invoke({'input': prompt})['output']
            logger.info(f"PDF summarization result for {event.src_path}: {output}")
            agent_data['last_pdf_summary'] = output
        except Exception as e:
            logger.error(f"Error processing PDF {event.src_path}: {str(e)}")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/list_agents', methods=['GET'])
def list_agents():
    try:
        agent_details = []
        for agent_id, agent_data in agents.items():
            agent_details.append({
                'agent_id': agent_id,
                'prompt': agent_data['prompt'],
                'interval': agent_data['interval'],
                'last_pdf_summary': agent_data['last_pdf_summary']
            })
        logger.info("Returning list of agents")
        return jsonify({'agents': agent_details})
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return jsonify({'error': f"Error listing agents: {str(e)}"}), 500

@app.route('/generate_agent', methods=['POST'])
def generate_agent():
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.error("Invalid JSON payload received")
            return jsonify({'error': 'Invalid JSON payload'}), 400

        prompt = data.get('prompt', '')
        if not prompt:
            logger.error("Prompt is required but was not provided")
            return jsonify({'error': 'Prompt is required'}), 400

        logger.info(f"Generating agent for prompt: {prompt}")
        agent = create_agent(available_tools, prompt)
        logger.info(f"Agent created successfully for prompt: {prompt}")
        agent_id = str(uuid.uuid4())
        
        agents[agent_id] = {
            'agent': agent,
            'prompt': prompt,
            'interval': data.get('interval', None),
            'last_pdf_summary': None
        }

        output = None
        if not ("summarize the pdf" in prompt.lower() or "summarize pdf" in prompt.lower()):
            try:
                logger.info(f"Invoking agent for initial run: {agent_id}")
                output = agent.invoke({'input': prompt})['output']
                logger.info(f"Initial run for agent {agent_id} successful: {output}")
            except Exception as e:
                logger.error(f"Error running agent {agent_id}: {str(e)}")
                return jsonify({'error': f"Error running agent: {str(e)}"}), 500
        else:
            output = "Agent created for PDF summarization. Please upload a PDF to proceed."

        interval = agents[agent_id]['interval']
        if interval and interval.strip():
            try:
                interval_minutes = float(interval)
                scheduler.add_job(
                    run_agent,
                    trigger=IntervalTrigger(minutes=interval_minutes),
                    args=[agent_id],
                    id=agent_id,
                    max_instances=1,
                    replace_existing=True
                )
                logger.info(f"Agent {agent_id} scheduled to run every {interval_minutes} minutes")
            except ValueError as e:
                logger.error(f"Invalid interval value '{interval}': {str(e)}")
                return jsonify({'error': f"Invalid interval value: {interval}"}), 400

        if "summarize the pdf" in prompt.lower() or "summarize pdf" in prompt.lower():
            try:
                observer = Observer()
                event_handler = PDFHandler(agent_id)
                observer.schedule(event_handler, UPLOAD_FOLDER, recursive=False)
                observer.start()
                agents[agent_id]['observer'] = observer
                logger.info(f"Started file monitoring for agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to start file monitoring for agent {agent_id}: {str(e)}")

        response = jsonify({'agent_id': agent_id, 'output': output})
        logger.info(f"Returning response for agent {agent_id}")
        return response
    except Exception as e:
        logger.error(f"Unexpected error in generate_agent: {str(e)}")
        return jsonify({'error': f"Unexpected error: {str(e)}"}), 500

@app.route('/run_agent/<agent_id>', methods=['GET'])
def run_agent_endpoint(agent_id):
    try:
        if agent_id not in agents:
            logger.error(f"Agent {agent_id} not found")
            return jsonify({'error': 'Agent not found'}), 404
        
        agent_data = agents[agent_id]
        agent = agent_data['agent']
        prompt = agent_data['prompt']
        
        logger.info(f"Manually running agent {agent_id} with prompt: {prompt}")
        output = agent.invoke({'input': prompt})['output']
        if agent_data.get('last_pdf_summary'):
            output += f"\nLast PDF Summary: {agent_data['last_pdf_summary']}"
        logger.info(f"Manual run for agent {agent_id} successful: {output}")
        return jsonify({'agent_id': agent_id, 'output': output})
    except Exception as e:
        logger.error(f"Error running agent {agent_id}: {str(e)}")
        return jsonify({'error': f"Error running agent: {str(e)}"}), 500

def run_agent(agent_id):
    try:
        if agent_id not in agents:
            logger.error(f"Agent {agent_id} not found for scheduled run")
            return
        
        agent_data = agents[agent_id]
        agent = agent_data['agent']
        prompt = agent_data['prompt']
        
        logger.info(f"Scheduled run started for agent {agent_id} with prompt: {prompt}")
        output = agent.invoke({'input': prompt})['output']
        logger.info(f"Scheduled run for agent {agent_id} successful: {output}")
    except Exception as e:
        logger.error(f"Error in scheduled run for agent {agent_id}: {str(e)}")

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            logger.error("No file part in the request")
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            logger.error(f"File {file.filename} is not a PDF")
            return jsonify({'error': 'File must be a PDF'}), 400

        file_content = file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        file.seek(0)

        for existing_file in os.listdir(UPLOAD_FOLDER):
            existing_file_path = os.path.join(UPLOAD_FOLDER, existing_file)
            if os.path.isfile(existing_file_path):
                with open(existing_file_path, 'rb') as f:
                    existing_content = f.read()
                    existing_hash = hashlib.md5(existing_content).hexdigest()
                if existing_hash == file_hash:
                    logger.info(f"Duplicate PDF detected. Using existing file: {existing_file_path}")
                    return jsonify({'file_path': existing_file_path, 'message': 'PDF already uploaded, using existing file'})

        filename = f"{uuid.uuid4()}.pdf"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        logger.info(f"PDF uploaded successfully: {file_path}")
        
        return jsonify({'file_path': file_path, 'message': 'PDF uploaded successfully'})
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        return jsonify({'error': f"Error uploading PDF: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
