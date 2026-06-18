# Enable anything we need available
source /etc/bashrc
source /etc/profile
source ~/.profile
source ~/.bashrc

# Print hostname so that it shows up in bpeek and the client knows where we are
hostname

# Start marimo with whatever environment uv finds in the given folder
# note that the server times out after 120 minutes of inactivity
cd $1
auv run marimo edit --host 0.0.0.0 --timeout 120
