#!/bin/bash

# Celebrity Voice Transformer - Raspberry Pi Setup Script
# This script installs all necessary dependencies and sets up the environment

# Set up error handling
set -e
trap 'echo "An error occurred. Setup failed."' ERR

# Output with colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function for printing status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$(id -u)" != "0" ]; then
   print_error "This script must be run as root. Try 'sudo ./setup_raspberry_pi.sh'"
   exit 1
fi

# Get current user (to avoid running pip as root)
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    USER_HOME=$HOME
fi

print_status "Starting setup for Celebrity Voice Transformer..."

# Update package lists
print_status "Updating package lists..."
apt-get update

# Install system dependencies
print_status "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    libportaudio2 \
    ffmpeg \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libasound2-dev \
    git

# Create project directory
PROJECT_DIR="$USER_HOME/celebrity-voice-transformer"
if [ ! -d "$PROJECT_DIR" ]; then
    print_status "Creating project directory..."
    mkdir -p "$PROJECT_DIR"
    chown -R "$SUDO_USER:$SUDO_USER" "$PROJECT_DIR"
fi

# Change to project directory
cd "$PROJECT_DIR"

# Create Python virtual environment
print_status "Creating Python virtual environment..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    sudo -u "$SUDO_USER" python3 -m venv venv
fi

# Clone or copy project files if not already present
if [ ! -f "$PROJECT_DIR/app.py" ]; then
    print_status "Copying project files..."
    
    # If the script is run from within the project directory, copy files
    if [ -f "$(dirname "$0")/app.py" ]; then
        cp -r "$(dirname "$0")"/* "$PROJECT_DIR"
        chown -R "$SUDO_USER:$SUDO_USER" "$PROJECT_DIR"
    else
        print_warning "Project files not found in script directory."
        print_warning "Please manually copy project files to $PROJECT_DIR"
    fi
fi

# Create required directories
print_status "Creating required directories..."
sudo -u "$SUDO_USER" mkdir -p "$PROJECT_DIR/temp_audio"
sudo -u "$SUDO_USER" mkdir -p "$PROJECT_DIR/output_audio"

# Install Python dependencies
print_status "Installing Python dependencies..."
sudo -u "$SUDO_USER" "$PROJECT_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$SUDO_USER" "$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# Ensure ormsgpack is installed (needed for Fish Audio ASR API)
print_status "Installing ormsgpack for Fish Audio ASR API..."
sudo -u "$SUDO_USER" "$PROJECT_DIR/venv/bin/pip" install ormsgpack

# Check for .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_status "Creating example .env file..."
    sudo -u "$SUDO_USER" cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env" 2>/dev/null || \
    cat > "$PROJECT_DIR/.env" << EOL
# Celebrity Voice Transformer Environment Variables

# OpenAI API Key
# Get this from https://platform.openai.com/account/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Fish Audio API Key
# Get this from https://fish.audio/ after creating an account
# This key is used for both TTS (Text-to-Speech) and ASR (Automatic Speech Recognition)
FISH_API_KEY=your_fish_audio_api_key_here

# Ngrok configuration (optional)
# Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTH_TOKEN=your_ngrok_auth_token_here
EOL
    chown "$SUDO_USER:$SUDO_USER" "$PROJECT_DIR/.env"
    print_warning "Don't forget to add your API keys to the .env file!"
fi

# Create a launcher script
print_status "Creating launcher script..."
cat > "$PROJECT_DIR/run_app.sh" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
source venv/bin/activate
streamlit run app.py
EOL

chmod +x "$PROJECT_DIR/run_app.sh"
chown "$SUDO_USER:$SUDO_USER" "$PROJECT_DIR/run_app.sh"

# Create a service file for autostart (optional)
print_status "Creating systemd service file (optional)..."
cat > "/etc/systemd/system/celebrity-voice-transformer.service" << EOL
[Unit]
Description=Celebrity Voice Transformer
After=network.target

[Service]
User=$SUDO_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/streamlit run app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

# Add ngrok installation to the script
if ! command -v ngrok &> /dev/null; then
    echo "Installing ngrok..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok
fi

print_status "Setup complete!"
print_status "You can now run the app by executing: $PROJECT_DIR/run_app.sh"
print_status "Or start the service with: sudo systemctl start celebrity-voice-transformer"
print_status "To enable automatic startup on boot: sudo systemctl enable celebrity-voice-transformer"
print_warning "Make sure to edit the .env file with your API keys before running the app!"
print_warning "Access the app via web browser at http://raspberry-pi-IP:8501"
print_status "The app now supports both Text-to-Speech (TTS) and Speech-to-Text (ASR) using Fish Audio API" 