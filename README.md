# Shayek شيّــك

Shayek شيّــك is a website that hosts news outlets with a built-in video Deepfake detection model.

## Goal
The goal behind Shayek is to provide a single platform that brings reliable news outlets together with no distractions,
<br> and to provide a video deepfake detection model that can limit the spread of misinformation.

## Technology
The website is developed using Flask, a Python web framework, for the back-end, with HTML, CSS, JavaScript, and AJAX handling the front-end.
<br>The models are built using Convolutional Neural Networks (CNN) with ResNet50 architecture.
### Tools: 
<ul>
  <li>Visual Studio Code</li>
  <li>Google Colab</li>
  <li>Firebase</li>
</ul>

## Launching Instructions
<ol>
    <li>
        <strong>Download the flask_shayek folder:</strong>
Click on the "Code" button and select "Download ZIP" to download the entire repository as a ZIP file, then extract the contents of the ZIP file to a location on your computer
    </li>
    <li>
        <strong>Create a virtual environment:</strong>
        Open a terminal or command prompt, make sure you're in the root directory of the project, then run the following commands to create and activate a virtual environment: <code>python -m venv venv</code>
        <br>On Windows: <code>venv\Scripts\activate</code>
        <br>On macOS and Linux: <code>source venv/bin/activate</code>
    </li>
    <li>
        <strong>Install any dependencies required:</strong>
        You can do that by installing the requirements.txt file: <code>pip install -r requirements.txt</code>
    </li>
    <li>
        <strong>Run the flask application:</strong>
        Run the following command to start the Flask development server <code>python run.py</code>
    </li>
    <li>
        <strong>Access the application:</strong>
        Once the Flask application is running, you can access it by opening a web browser and navigating to <code>http://localhost:5000</code> or another port specified in your Flask application configuration.
    </li>
  </ol>
<strong>Shutting down the application:</strong>
To stop the Flask development server, you can press Ctrl + C for Windows, or Command + C for macOS and Linux, in the terminal/command prompt where the server is running.
