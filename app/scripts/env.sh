# Araç zincirini bu kabuğa yükler (kabuk profillerine dokunulmadan kuruldu).
#   source app/scripts/env.sh
# rustup: ~/.cargo, ~/.rustup · nvm + Node 22 LTS: ~/.nvm
if [ -f "$HOME/.cargo/env" ]; then . "$HOME/.cargo/env"; fi
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then . "$NVM_DIR/nvm.sh" >/dev/null && nvm use --silent default >/dev/null; fi
