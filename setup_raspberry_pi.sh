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

print_status "Starting setup for Voice Processing Application..."

# Function to check if a package is installed
is_package_installed() {
    dpkg -l "$1" &> /dev/null
}

# Create a list of packages to install
PACKAGES_TO_INSTALL=()

# Check each package and add to installation list if not present
REQUIRED_PACKAGES=(
    "python3"
    "python3-pip"
    "python3-venv"
    "portaudio19-dev"
    "libportaudio2"
    "ffmpeg"
    "libatlas-base-dev"
    "libhdf5-dev"
    "libasound2-dev"
    "git"
    "curl"
    "build-essential"
    "pkg-config"
    "libssl-dev"
    "flac"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! is_package_installed "$package"; then
        PACKAGES_TO_INSTALL+=("$package")
    fi
done

# Only update and install if there are packages to install
if [ ${#PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
    print_status "Installing missing system dependencies: ${PACKAGES_TO_INSTALL[*]}"
    apt-get -qq update > /dev/null 2>&1
    apt-get -qq install --no-install-recommends -y "${PACKAGES_TO_INSTALL[@]}" > /dev/null 2>&1
else
    print_status "All system dependencies are already installed"
fi

# Use current directory instead of creating a new one
PROJECT_DIR=$(pwd)
print_status "Using current directory: $PROJECT_DIR"

# Create required directories if they don't exist
print_status "Creating required directories..."
sudo -u "$SUDO_USER" mkdir -p "$PROJECT_DIR/temp_audio"
sudo -u "$SUDO_USER" mkdir -p "$PROJECT_DIR/output_audio"

# Create Python virtual environment only if it doesn't exist
print_status "Checking Python virtual environment..."
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    print_status "Creating new virtual environment..."
    sudo -u "$SUDO_USER" python3 -m venv .venv
else
    print_status "Virtual environment already exists"
fi

# Install Python dependencies only if requirements.txt has changed
REQUIREMENTS_HASH_FILE="$PROJECT_DIR/.venv/.requirements.hash"
CURRENT_HASH=$(md5sum requirements.txt | cut -d' ' -f1)
STORED_HASH=""
if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
    STORED_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
fi

if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
    print_status "Installing/updating Python dependencies..."
    sudo -u "$SUDO_USER" bash -c "source .venv/bin/activate && \
        pip install --no-cache-dir --no-deps --upgrade pip > /dev/null 2>&1 && \
        pip install --no-cache-dir wheel > /dev/null 2>&1 && \
        pip install --no-cache-dir -r requirements.txt > /dev/null 2>&1"
    echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
else
    print_status "Python dependencies are up to date"
fi

# Check for .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_status "Creating example .env file..."
    sudo -u "$SUDO_USER" cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env" 2>/dev/null || \
    cat > "$PROJECT_DIR/.env" << EOL
# Voice Processing Application Environment Variables

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

# Create or update launcher script
print_status "Creating launcher script..."
cat > "$PROJECT_DIR/launch.sh" << 'EOL'
#!/bin/bash

# Set up error handling
set -e
trap 'echo "An error occurred. Application failed to start."' ERR

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function for status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to script directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found. Please run setup_raspberry_pi.sh first"
    exit 1
fi

# Check if required files exist
for file in "app.py" "run.py" "requirements.txt"; do
    if [ ! -f "$file" ]; then
        print_error "Required file $file not found"
        exit 1
    fi
done

# Check if .env exists and has API keys
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it from .env.example"
    exit 1
fi

# Activate virtual environment and run the application
print_status "Starting Voice Processing Application..."
source .venv/bin/activate

# Check if all required Python packages are installed
if ! pip freeze > /dev/null 2>&1; then
    print_error "Python packages not properly installed. Try running setup_raspberry_pi.sh again"
    exit 1
fi

# Run the application
print_status "Launching application..."
python run.py
EOL

# Make the launcher executable and set proper ownership
chmod +x "$PROJECT_DIR/launch.sh"
chown "$SUDO_USER:$SUDO_USER" "$PROJECT_DIR/launch.sh"

print_status "Launch script created at $PROJECT_DIR/launch.sh"

# Install ngrok only if not already installed
if ! command -v ngrok &> /dev/null; then
    print_status "Installing ngrok..."
    if ! grep -q "ngrok-agent" /etc/apt/sources.list.d/ngrok.list 2>/dev/null; then
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list >/dev/null
        apt-get -qq update > /dev/null 2>&1
    fi
    apt-get -qq install -y ngrok > /dev/null 2>&1
else
    print_status "ngrok is already installed"
fi

print_status "Setup complete!"
print_status "You can now run the app by executing: ./launch.sh"
print_warning "Make sure to edit the .env file with your API keys before running the app!"
print_status "The app supports both Text-to-Speech (TTS) and Speech-to-Text (ASR) using Fish Audio API" 