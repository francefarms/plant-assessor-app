import os
from flask import Flask, request, render_template, jsonify
import tensorflow as tf
from tensorflow.keras.models import load_model # Used to load the saved model
import numpy as np
import cv2 # OpenCV for image processing

# --- Configuration ---
UPLOAD_FOLDER = 'uploads' # Folder to temporarily save uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'} # Allowed image file extensions
MODEL_PATH = 'plant_growth_model.h5' # Path to your saved model file

# --- Initialize Flask App ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Load the Trained Model and Class Names ---
# IMPORTANT: These class names must match the order in which your model was trained.
# Based on your previous output, it should be ['healthy_', 'unhealthy_']
try:
    model = load_model(MODEL_PATH)
    # Define class names based on your dataset structure
    # You might need to adjust this if your folder names differ or you add more classes
    class_names = ['healthy_', 'unhealthy_'] # Manually set based on your detected classes
    IMG_HEIGHT, IMG_WIDTH = model.input_shape[1], model.input_shape[2]
    print(f"Model '{MODEL_PATH}' loaded successfully.")
    print(f"Model expects input shape: ({IMG_HEIGHT}, {IMG_WIDTH}, 3)")
    print(f"Detected class names for prediction: {class_names}")

except Exception as e:
    print(f"Error loading model: {e}")
    print("Please ensure 'plant_growth_model.h5' is in the same directory as this app.py.")
    print("Also, ensure TensorFlow and Keras versions are compatible with the saved model.")
    model = None # Set model to None if loading fails to prevent further errors

# --- Helper function for allowed file types ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Image Preprocessing Function (from your original script) ---
def preprocess_image_for_prediction(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    img = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # Convert BGR to RGB
    img = img / 255.0 # Normalize
    img = np.expand_dims(img, axis=0) # Add batch dimension
    return img

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded. Cannot make predictions.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file.'}), 400
    if file and allowed_file(file.filename):
        # Save the uploaded file temporarily
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # Preprocess the image
        processed_img = preprocess_image_for_prediction(filepath)

        # Remove the temporary file after processing
        os.remove(filepath)

        if processed_img is None:
            return jsonify({'error': 'Could not process image.'}), 400

        # Make prediction
        predictions = model.predict(processed_img)
        predicted_class_index = np.argmax(predictions[0])
        predicted_class_name = class_names[predicted_class_index]
        confidence = predictions[0][predicted_class_index] * 100

        return jsonify({
            'predicted_class': predicted_class_name,
            'confidence': f"{confidence:.2f}%"
        })
    else:
        return jsonify({'error': 'Allowed image types are png, jpg, jpeg'}), 400

# --- Run the App ---
if __name__ == '__main__':
    # Set debug to True for development, set to False for production
    # For Heroku deployment, use port from environment variable and set debug to False
    port = int(os.environ.get('PORT', 5000)) # Get port from Heroku, default to 5000 for local testing
    app.run(debug=False, host='0.0.0.0', port=port)
