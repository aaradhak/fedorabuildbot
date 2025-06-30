#!/usr/bin/env python3
"""
Fedora CoreOS Assembler (COSA) Chatbot
An intelligent chatbot for building different Fedora CoreOS streams using COSA commands.
Supports automatic branch switching and stream-specific builds.
"""

import os
import sys
import subprocess
import shlex
import time
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

class FedoraCOSABot:
    def __init__(self, work_dir: str = "./fcos"):
        self.work_dir = Path(work_dir).resolve()
        self.container_image = "quay.io/coreos-assembler/coreos-assembler:latest"
        self.config_repo = "https://github.com/coreos/fedora-coreos-config"
        self.initialized = False
        self.current_stream = None
        self.available_streams = ["testing-devel", "stable", "testing", "next", "rawhide"]
        
        # Build state tracking
        self.build_states = {}  # stream -> {fetched: bool, built: bool}
        
        # Create working directory if it doesn't exist
        self.work_dir.mkdir(exist_ok=True)
        os.chdir(self.work_dir)
        
        print(f"🤖 Fedora CoreOS Bot initialized in: {self.work_dir}")
        print(f"📡 Config repository: {self.config_repo}")
        
    def check_prerequisites(self) -> bool:
        """Check if required tools are available"""
        try:
            # Check for podman
            result = subprocess.run(['podman', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Podman not found. Please install podman first.")
                return False
                
            # Check for git
            result = subprocess.run(['git', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Git not found. Please install git first.")
                return False
                
            # Check for /dev/kvm
            if not os.path.exists('/dev/kvm'):
                print("⚠️  /dev/kvm not found. Virtualization may not work properly.")
                print("   Make sure you have KVM enabled or are running on bare metal.")
                
            print("✅ Prerequisites check passed!")
            return True
            
        except FileNotFoundError:
            print("❌ Required tools not found. Please install podman and git.")
            return False
    
    def pull_container(self) -> bool:
        """Pull the COSA container image"""
        print(f"📥 Pulling COSA container: {self.container_image}")
        
        try:
            result = subprocess.run([
                'podman', 'pull', self.container_image
            ], check=True)
            
            print("✅ Container pulled successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to pull container: {e}")
            return False
    
    def run_cosa_command(self, command: str, interactive: bool = True) -> bool:
        """Execute a COSA command in the container"""
        
        # Build the podman command based on the document
        podman_cmd = [
            'podman', 'run', '--rm',
            '--security-opt=label=disable',
            '--privileged',
            '--userns=keep-id:uid=1000,gid=1000',
            f'-v={self.work_dir}:/srv/',
            '--device=/dev/kvm',
            '--device=/dev/fuse',
            '--tmpfs=/tmp',
            '-v=/var/tmp:/var/tmp',
            '--name=cosa',
            self.container_image
        ]
        
        if interactive:
            podman_cmd.insert(2, '-ti')
        
        podman_cmd.extend(shlex.split(command))
        
        print(f"🚀 Running: cosa {command}")
        
        try:
            if interactive:
                result = subprocess.run(podman_cmd)
            else:
                result = subprocess.run(podman_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Command completed successfully!")
                return True
            else:
                print(f"❌ Command failed with exit code: {result.returncode}")
                if not interactive and result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            return False
        except KeyboardInterrupt:
            print("\n⚠️  Command interrupted by user")
            return False
    
    def get_available_branches(self) -> List[str]:
        """Get available branches from the config repository"""
        config_dir = self.work_dir / "src" / "config"
        if not config_dir.exists():
            return self.available_streams
            
        try:
            # First, fetch from remote to get all branches
            subprocess.run([
                'git', '-C', str(config_dir), 'fetch', 'origin'
            ], capture_output=True, text=True)
            
            # Get remote branches
            result = subprocess.run([
                'git', '-C', str(config_dir), 'branch', '-r'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                branches = []
                for line in result.stdout.split('\n'):
                    if 'origin/' in line and '->' not in line:
                        branch = line.strip().replace('origin/', '')
                        if branch and branch != 'HEAD':
                            branches.append(branch)
                return branches
            
        except Exception as e:
            print(f"⚠️  Could not fetch branches: {e}")
            
        return self.available_streams
    
    def switch_to_stream(self, stream: str) -> bool:
        """Switch to a specific Fedora CoreOS stream/branch"""
        config_dir = self.work_dir / "src" / "config"
        
        if not config_dir.exists():
            print(f"❌ Config directory not found. Please run 'cosa init' first!")
            return False
            
        print(f"🔄 Switching to stream: {stream}")
        
        try:
            # First, fetch latest from remote to ensure we have all branches
            print("📡 Fetching latest branches from remote...")
            subprocess.run([
                'git', '-C', str(config_dir), 'fetch', 'origin'
            ], check=True, capture_output=True)
            
            # Try to switch to the branch, first try as a local branch
            result = subprocess.run([
                'git', '-C', str(config_dir), 'checkout', stream
            ], capture_output=True, text=True)
            
            # If that fails, try as a remote branch
            if result.returncode != 0:
                result = subprocess.run([
                    'git', '-C', str(config_dir), 'checkout', '-b', stream, f'origin/{stream}'
                ], capture_output=True, text=True)
            
            # If still fails, try switching to origin/stream directly
            if result.returncode != 0:
                result = subprocess.run([
                    'git', '-C', str(config_dir), 'checkout', f'origin/{stream}'
                ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.current_stream = stream
                print(f"✅ Switched to stream: {stream}")
                
                # Reset build state for this stream
                if stream not in self.build_states:
                    self.build_states[stream] = {'fetched': False, 'built': False}
                    
                return True
            else:
                print(f"❌ Failed to switch to stream '{stream}': {result.stderr}")
                available = self.get_available_branches()
                print(f"Available streams: {', '.join(available)}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False
    
    def is_cosa_initialized(self) -> bool:
        """Check if COSA is already initialized by looking for expected structure"""
        config_dir = self.work_dir / "src" / "config"
        cache_dir = self.work_dir / "cache"
        
        # Check for key COSA directories/files
        if (config_dir.exists() and 
            cache_dir.exists() and
            (config_dir / ".git").exists()):
            return True
        return False
    
    def cosa_init(self, config_repo: str = None, force: bool = False) -> bool:
        """Initialize COSA with the configuration repository"""
        
        # Check if already initialized
        if self.is_cosa_initialized():
            self.initialized = True
            print("ℹ️  COSA already initialized!")
            
            # Get current branch
            config_dir = self.work_dir / "src" / "config"
            try:
                result = subprocess.run([
                    'git', '-C', str(config_dir), 'branch', '--show-current'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    current_branch = result.stdout.strip()
                    if current_branch:
                        self.current_stream = current_branch
                        print(f"📋 Current stream: {current_branch}")
                    
            except Exception:
                pass
            return True
            
        repo = config_repo or self.config_repo
        
        # Check if directory is not empty
        existing_items = list(self.work_dir.iterdir())
        if existing_items and not force:
            print(f"⚠️  Working directory is not empty ({len(existing_items)} items found)")
            print("   COSA init requires an empty directory or --force flag")
            print("   Options:")
            print("   1. Use 'force-init' to initialize anyway")
            print("   2. Use 'clean-dir' to clean the directory first")
            print("   3. Choose a different working directory")
            return False
        
        init_cmd = f"init {repo}"
        if force:
            init_cmd += " --force"
            print(f"🔧 Force initializing COSA with config repo: {repo}")
        else:
            print(f"🔧 Initializing COSA with config repo: {repo}")
        
        success = self.run_cosa_command(init_cmd)
        if success:
            self.initialized = True
            print("✅ COSA initialized successfully!")
            
            # Check if config was cloned
            config_dir = self.work_dir / "src" / "config"
            if config_dir.exists():
                print(f"📁 Configuration cloned to: {config_dir}")
                
                # Get current branch
                try:
                    result = subprocess.run([
                        'git', '-C', str(config_dir), 'branch', '--show-current'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        current_branch = result.stdout.strip()
                        if current_branch:
                            self.current_stream = current_branch
                            print(f"📋 Current stream: {current_branch}")
                        
                except Exception:
                    pass
            
        return success
    
    def cosa_fetch(self, stream: str = None) -> bool:
        """Fetch metadata and packages for a specific stream"""
        if not self.initialized:
            print("❌ Please run 'cosa init' first!")
            return False
            
        # Check disk space before fetching
        if not self.check_disk_space():
            print("💡 Try running 'clean' or 'clean-all' to free up space")
            user_input = input("Continue anyway? (y/N): ").strip().lower()
            if user_input not in ['y', 'yes']:
                return False
            
        # Switch to stream if specified
        if stream and stream != self.current_stream:
            if not self.switch_to_stream(stream):
                return False
                
        current = self.current_stream or "current"
        print(f"📦 Fetching metadata and packages for stream: {current}")
        
        success = self.run_cosa_command("fetch")
        if success:
            if current not in self.build_states:
                self.build_states[current] = {'fetched': False, 'built': False}
            self.build_states[current]['fetched'] = True
            print(f"✅ Fetch completed for stream: {current}")
            
        return success
    
    def cosa_build(self, stream: str = None) -> bool:
        """Build the CoreOS image for a specific stream"""
        if not self.initialized:
            print("❌ Please run 'cosa init' first!")
            return False
            
        # Check disk space before building
        if not self.check_disk_space():
            print("💡 Try running 'clean' or 'clean-all' to free up space")
            user_input = input("Continue anyway? (y/N): ").strip().lower()
            if user_input not in ['y', 'yes']:
                return False
            
        # Switch to stream if specified
        if stream and stream != self.current_stream:
            if not self.switch_to_stream(stream):
                return False
                
        current = self.current_stream or "current"
        
        # Check if fetch was done for this stream
        if (current not in self.build_states or 
            not self.build_states[current].get('fetched', False)):
            print(f"⚠️  Stream '{current}' not fetched yet. Running fetch first...")
            if not self.cosa_fetch():
                return False
        
        print(f"🔨 Building CoreOS image for stream: {current}")
        print("⏰ This may take a while...")
        
        success = self.run_cosa_command("build")
        if success:
            self.build_states[current]['built'] = True
            print(f"✅ Build completed for stream: {current}")
            
            # Check for build output
            builds_dir = self.work_dir / "builds"
            if builds_dir.exists():
                latest_link = builds_dir / "latest"
                if latest_link.exists():
                    print(f"🔗 Latest build: {latest_link}")
            
        return success
    
    def build_stream(self, stream: str) -> bool:
        """Automated workflow to build a specific stream"""
        print(f"🚀 Starting automated build for stream: {stream}")
        
        # Initialize if not done
        if not self.initialized and not self.is_cosa_initialized():
            print("📋 Initializing COSA...")
            if not self.cosa_init():
                print("💡 If the directory is not empty, try 'force-init' or 'clean-dir'")
                return False
        elif not self.initialized:
            # Directory has COSA structure but not marked as initialized
            self.initialized = True
            print("📋 Detected existing COSA initialization")
        
        # Switch to stream
        if not self.switch_to_stream(stream):
            return False
            
        # Fetch and build
        print(f"📦 Fetching packages for {stream}...")
        if not self.cosa_fetch():
            return False
            
        print(f"🔨 Building {stream} image...")
        if not self.cosa_build():
            return False
            
        print(f"🎉 Successfully built Fedora CoreOS {stream}!")
        print(f"   You can now:")
        print(f"     • 'run' - Start the VM")
        print(f"     • 'kola list' - See available tests")
        print(f"     • 'run basic test' - Run basic tests")
        print(f"     • 'run podman test' - Run podman tests")
        print(f"     • 'kola interactive' - Run tests interactively")
        return True
    
    def kola_list_tests(self) -> bool:
        """List available kola tests"""
        if not self.initialized:
            print("❌ Please initialize COSA first!")
            return False
            
        current = self.current_stream or "current"
        
        if (current not in self.build_states or 
            not self.build_states[current].get('built', False)):
            print(f"❌ No build found for stream '{current}'. Please build first!")
            return False
            
        print(f"📋 Listing available kola tests for stream: {current}")
        
        success = self.run_cosa_command("kola list", interactive=False)
        return success
    
    def kola_run_tests(self, test_pattern: str = "", custom_args: str = "") -> bool:
        """Run kola tests with optional pattern and arguments"""
        if not self.initialized:
            print("❌ Please initialize COSA first!")
            return False
            
        current = self.current_stream or "current"
        
        if (current not in self.build_states or 
            not self.build_states[current].get('built', False)):
            print(f"❌ No build found for stream '{current}'. Please build first!")
            return False
            
        # Build the kola command
        if test_pattern:
            command = f"kola run {test_pattern}"
            print(f"🧪 Running kola tests matching pattern: {test_pattern}")
        else:
            command = "kola run"
            print(f"🧪 Running all kola tests for stream: {current}")
            
        if custom_args:
            command += f" {custom_args}"
            print(f"   Additional args: {custom_args}")
            
        print("⏰ This may take a while depending on the number of tests...")
        
        success = self.run_cosa_command(command)
        if success:
            print(f"✅ Kola tests completed for stream: {current}")
        else:
            print(f"❌ Some kola tests failed for stream: {current}")
            
        return success
    
    def kola_run_specific_tests(self) -> bool:
        """Interactive test selection and execution"""
        if not self.initialized:
            print("❌ Please initialize COSA first!")
            return False
            
        current = self.current_stream or "current"
        
        if (current not in self.build_states or 
            not self.build_states[current].get('built', False)):
            print(f"❌ No build found for stream '{current}'. Please build first!")
            return False
            
        print(f"🧪 Interactive Kola Test Runner for stream: {current}")
        print("   First, let's see available tests...")
        
        # Get list of tests
        result = self.run_cosa_command("kola list", interactive=False)
        if not result:
            print("❌ Could not retrieve test list")
            return False
            
        print("\n💡 Test Selection Options:")
        print("   1. Run all tests: just press Enter")
        print("   2. Run specific test: enter test name (e.g., 'basic')")
        print("   3. Run test pattern: use wildcards (e.g., 'basic.*')")
        print("   4. Run multiple tests: separate with spaces (e.g., 'basic podman')")
        print("   5. Cancel: type 'cancel'")
        
        user_input = input("\n🧪 Enter test pattern or name: ").strip()
        
        if user_input.lower() == 'cancel':
            print("❌ Test execution cancelled")
            return False
            
        # Ask for additional arguments
        print("\n💡 Additional Arguments (optional):")
        print("   --parallel=N     - Run N tests in parallel") 
        print("   --qemu-image=X   - Use specific image")
        print("   --timeout=Xs     - Set timeout (e.g., 300s)")
        
        custom_args = input("🔧 Additional args (or press Enter): ").strip()
        
        return self.kola_run_tests(user_input, custom_args)
    
    def show_test_summary(self):
        """Show testing status summary"""
        print(f"\n🧪 Kola Testing Summary:")
        
        if not self.initialized:
            print("   ❌ COSA not initialized")
            return
            
        tested_streams = 0
        for stream, state in self.build_states.items():
            if state.get('built', False):
                print(f"   📦 {stream}: Build available - ready for testing")
                tested_streams += 1
            elif state.get('fetched', False):
                print(f"   📋 {stream}: Fetched only - need to build first")
            else:
                print(f"   ❌ {stream}: Not ready")
                
        if tested_streams == 0:
            print("   💡 No builds available for testing. Build an image first!")
        else:
            print(f"   ✅ {tested_streams} stream(s) ready for testing")
            print("   💡 Use 'kola list' to see available tests")

    def cosa_run(self, custom_args: str = "") -> bool:
        """Run the built CoreOS image"""
        current = self.current_stream or "latest"
        
        if (current not in self.build_states or 
            not self.build_states[current].get('built', False)):
            print(f"❌ No build found for stream '{current}'. Please build first!")
            return False
            
        print(f"🚀 Starting CoreOS VM (stream: {current})...")
        print("💡 Use Ctrl-a x to exit QEMU")
        
        command = f"run {custom_args}".strip()
        return self.run_cosa_command(command)
    
    def check_disk_space(self):
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.work_dir)
            
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            free_percent = (free / total) * 100
            
            print(f"\n💾 Disk Space Status:")
            print(f"   📁 Working Directory: {self.work_dir}")
            print(f"   💿 Total: {total_gb:.1f} GB")
            print(f"   📊 Used: {used_gb:.1f} GB")
            print(f"   🆓 Free: {free_gb:.1f} GB ({free_percent:.1f}%)")
            
            if free_gb < 10:
                print(f"   ⚠️  WARNING: Low disk space! CoreOS builds need 10-20 GB")
                return False
            elif free_gb < 5:
                print(f"   ❌ CRITICAL: Very low disk space! Build will likely fail")
                return False
            else:
                print(f"   ✅ Sufficient space available")
                return True
                
        except Exception as e:
            print(f"   ❌ Could not check disk space: {e}")
            return True
    
    def clean_directory(self) -> bool:
        """Clean the working directory completely"""
        try:
            existing_items = list(self.work_dir.iterdir())
            if not existing_items:
                print("📁 Directory is already empty")
                return True
                
            print(f"🧹 Cleaning working directory ({len(existing_items)} items)...")
            print("⚠️  This will remove ALL files in the working directory!")
            user_input = input("Continue? (y/N): ").strip().lower()
            
            if user_input not in ['y', 'yes']:
                print("❌ Directory cleaning cancelled")
                return False
                
            for item in existing_items:
                print(f"   🗑️  Removing: {item.name}")
                if item.is_dir():
                    subprocess.run(['rm', '-rf', str(item)], check=True)
                else:
                    item.unlink()
                    
            print("✅ Directory cleaned successfully")
            
            # Reset state
            self.initialized = False
            self.current_stream = None
            self.build_states = {}
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to clean directory: {e}")
            return False

    def clean_builds(self, keep_latest: bool = True) -> bool:
        """Clean old build artifacts to free up space"""
        builds_dir = self.work_dir / "builds"
        if not builds_dir.exists():
            print("📁 No builds directory found - nothing to clean")
            return True
            
        try:
            build_dirs = [d for d in builds_dir.iterdir() if d.is_dir() and d.name != "latest"]
            
            if not build_dirs:
                print("🧹 No old builds to clean")
                return True
                
            print(f"🧹 Cleaning {len(build_dirs)} old build(s)...")
            
            for build_dir in build_dirs:
                if keep_latest and build_dir.name == "latest":
                    continue
                    
                print(f"   🗑️  Removing: {build_dir.name}")
                subprocess.run(['rm', '-rf', str(build_dir)], check=True)
                
            print("✅ Build cleanup completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to clean builds: {e}")
            return False
    
    def clean_containers(self) -> bool:
        """Clean unused podman containers and images"""
        try:
            print("🧹 Cleaning unused containers and images...")
            
            # Remove stopped containers
            result = subprocess.run(['podman', 'container', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ Cleaned stopped containers")
            
            # Remove unused images (but keep COSA image)
            result = subprocess.run(['podman', 'image', 'prune', '-f'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ Cleaned unused images")
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to clean containers: {e}")
            return False

    def show_status(self):
        """Show current build status"""
        print(f"\n📊 Fedora CoreOS Build Status:")
        print(f"   Working Directory: {self.work_dir}")
        print(f"   ✅ Initialized: {'Yes' if self.initialized else 'No'}")
        print(f"   📋 Current Stream: {self.current_stream or 'None'}")
        
        if self.build_states:
            print(f"   🔨 Build States:")
            for stream, state in self.build_states.items():
                fetched = "✅" if state.get('fetched', False) else "❌"
                built = "✅" if state.get('built', False) else "❌"
                print(f"      {stream}: Fetched {fetched} | Built {built}")
        
        # Check for actual artifacts
        config_dir = self.work_dir / "src" / "config"
        if config_dir.exists():
            print(f"   📁 Config repo: Present")
            available = self.get_available_branches()
            print(f"   🌿 Available streams: {', '.join(available[:5])}{'...' if len(available) > 5 else ''}")
            
        builds_dir = self.work_dir / "builds"
        if builds_dir.exists():
            build_dirs = [d for d in builds_dir.iterdir() if d.is_dir()]
            print(f"   📦 Total builds: {len(build_dirs)}")
            if (builds_dir / "latest").exists():
                print(f"   🔗 Latest build: Available")
                
        # Show disk space
        self.check_disk_space()
    
    def refresh_branches(self) -> bool:
        """Fetch all remote branches and show available streams"""
        config_dir = self.work_dir / "src" / "config"
        
        if not config_dir.exists():
            print("❌ Config directory not found. Please run 'init' first!")
            return False
            
        try:
            print("📡 Fetching all remote branches...")
            subprocess.run([
                'git', '-C', str(config_dir), 'fetch', 'origin'
            ], check=True)
            
            print("✅ Remote branches updated!")
            self.list_streams()
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to fetch remote branches: {e}")
            return False

    def list_streams(self):
        """List available Fedora CoreOS streams"""
        if not self.initialized:
            print("Available streams (estimated): testing-devel, stable, testing, next, rawhide")
            print("💡 Run 'init' first to get the actual list from the repository")
            return
            
        streams = self.get_available_branches()
        print(f"\n🌿 Available Fedora CoreOS streams:")
        
        for stream in streams:
            status = ""
            if stream in self.build_states:
                state = self.build_states[stream]
                if state.get('built', False):
                    status = "🏗️  Built"
                elif state.get('fetched', False):
                    status = "📦 Fetched"
            
            current_marker = "👉 " if stream == self.current_stream else "   "
            print(f"{current_marker}{stream} {status}")
            
        if not streams or len(streams) <= 1:
            print("\n💡 If you only see one stream, try 'refresh' to fetch all remote branches")
    
    def show_help(self):
        """Show available commands"""
        print("""
🤖 Fedora CoreOS Bot Commands:

Quick Build Commands:
  build <stream>     - Automatically build a specific stream (e.g., 'build rawhide')
  build stable       - Build the stable release
  build testing      - Build the testing release  
  build testing-devel- Build the testing development version
  build next         - Build the next release
  build rawhide      - Build the latest development version
  
Testing Commands:
  kola list          - List all available kola tests
  kola run [pattern] - Run kola tests (all tests or matching pattern)
  kola interactive   - Interactive test selection and execution
  test [pattern]     - Shorthand for kola run
  run [test] test    - Natural language test runner (e.g., "run basic test")
  run [test]         - Run specific test (e.g., "run basic", "run podman")
  test-summary       - Show testing status for all streams
  
Manual Build Commands:
  init [repo]        - Initialize COSA (default: fedora-coreos-config)
  force-init [repo]  - Force initialize COSA (override non-empty directory)
  fetch [stream]     - Fetch packages for current or specified stream
  build [stream]     - Build image for current or specified stream
  run [args]         - Run the built CoreOS VM
  
Stream Management:
  streams            - List available streams/branches
  refresh            - Fetch all remote branches and update stream list
  switch <stream>    - Switch to a different stream
  current            - Show current stream
  
Utility Commands:
  status             - Show detailed build status and disk space
  pull               - Pull latest COSA container
  shell              - Open shell in COSA container
  disk               - Check disk space usage
  clean              - Clean old builds to free space
  clean-all          - Clean builds and unused containers
  clean-dir          - Clean entire working directory
  help               - Show this help message
  quit/exit          - Exit the bot

🚀 Quick Start Examples:
  "build rawhide"      - Build the latest Fedora CoreOS development version
  "build stable"       - Build the stable release
  "build testing-devel"- Build the testing development version
  "kola list"          - See all available tests after building
  "run basic test"     - Run basic kola tests (natural language)
  "run basic"          - Run basic tests (shorthand)
  "run podman test"    - Run podman-related tests
  "kola interactive"   - Interactively select and run tests
  "run"                - Start the CoreOS VM (no args = VM, with test name = kola)
  "switch next"        - Switch to next stream, then "fetch" and "build"

💡 Tips:
  - Different streams correspond to different git branches
  - The bot tracks build state per stream automatically  
  - CoreOS builds require 10-20 GB of free disk space
  - After building, use natural language: 'run basic test', 'run podman test'
  - Use 'run' alone to start VM, 'run [test]' to run kola tests
  - Use 'kola list' to see all available tests
  - Use 'disk' to check space and 'clean' to free up space
  - If init fails with "directory not empty", use 'force-init' or 'clean-dir'
  - If streams are missing, use 'refresh' to fetch all remote branches
  - Use 'status' to see what's been built for each stream
  - All data persists in the working directory
        """)
    
    def parse_command(self, user_input: str) -> tuple:
        """Parse user input into command and arguments"""
        parts = user_input.strip().split()
        if not parts:
            return None, []
            
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Handle natural language patterns
        if command == "build" and len(args) == 1:
            return "build_stream", args
        elif command in ["switch", "checkout"] and len(args) == 1:
            return "switch", args
        elif command in ["streams", "branches", "list"]:
            return "list_streams", []
        elif command in ["refresh", "update", "fetch-branches"]:
            return "refresh", []
        elif command == "current":
            return "current_stream", []
        elif command == "force-init":
            return "force-init", args
        elif command in ["clean-dir", "clean-directory"]:
            return "clean-dir", []
        elif command == "kola":
            if not args:
                return "kola_help", []
            elif args[0].lower() == "list":
                return "kola_list", []
            elif args[0].lower() == "run":
                return "kola_run", args[1:]  # Pass remaining args as test pattern
            elif args[0].lower() == "interactive":
                return "kola_interactive", []
            else:
                return "kola_run", args  # Treat first arg as test pattern
        elif command == "test":
            return "kola_run", args  # Shorthand for kola run
        elif command == "test-summary":
            return "test_summary", []
        elif command == "run":
            # Smart parsing for "run" command
            if not args:
                # "run" alone -> start VM
                return "run_vm", []
            elif len(args) == 1:
                # Check if it looks like a test name or VM args
                test_indicators = ["basic", "podman", "network", "internet", "coreos", "ostree", "rpmostree", "systemd"]
                if any(indicator in args[0].lower() for indicator in test_indicators):
                    # "run basic" -> run kola test
                    return "kola_run", args
                else:
                    # "run --some-vm-arg" -> start VM with args
                    return "run_vm", args
            elif len(args) >= 2 and args[-1].lower() in ["test", "tests"]:
                # "run basic test" or "run basic tests" -> run kola test
                test_pattern = " ".join(args[:-1])  # Remove "test/tests" from the end
                return "kola_run", [test_pattern]
            elif any(word in " ".join(args).lower() for word in ["test", "kola"]):
                # Contains "test" or "kola" -> run kola test
                return "kola_run", args
            else:
                # Default to VM run with args
                return "run_vm", args
            
        return command, args

    def interactive_mode(self):
        """Run the chatbot in interactive mode"""
        print("🤖 Welcome to Fedora CoreOS Bot!")
        print("   Build different CoreOS streams and run kola tests")
        print("   Try: 'build rawhide', then 'kola list' and 'run basic test'")
        print("   Type 'help' for all available commands")
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("❌ Prerequisites not met. Please fix the issues above.")
            return
            
        while True:
            try:
                user_input = input(f"\n🤖 fcos-bot ({self.current_stream or 'none'})> ").strip()
                
                if not user_input:
                    continue
                    
                command, args = self.parse_command(user_input)
                
                if command in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                    
                elif command == 'help':
                    self.show_help()
                    
                elif command == 'status':
                    self.show_status()
                    
                elif command == 'pull':
                    self.pull_container()
                    
                elif command == 'init':
                    repo = args[0] if args else None
                    self.cosa_init(repo)
                    
                elif command == 'force-init':
                    repo = args[0] if args else None
                    self.cosa_init(repo, force=True)
                    
                elif command == 'fetch':
                    stream = args[0] if args else None
                    self.cosa_fetch(stream)
                    
                elif command == 'build':
                    stream = args[0] if args else None
                    self.cosa_build(stream)
                    
                elif command == 'build_stream':
                    if args:
                        self.build_stream(args[0])
                    else:
                        print("❌ Please specify a stream to build (e.g., 'build rawhide')")
                        
                elif command == 'switch':
                    if args:
                        self.switch_to_stream(args[0])
                    else:
                        print("❌ Please specify a stream to switch to")
                        
                elif command == 'current_stream':
                    if self.current_stream:
                        print(f"📋 Current stream: {self.current_stream}")
                    else:
                        print("📋 No stream selected (run 'init' first)")
                        
                elif command == 'list_streams':
                    self.list_streams()
                    
                elif command == 'refresh':
                    self.refresh_branches()
                    
                elif command == 'run_vm':
                    custom_args = " ".join(args) if args else ""
                    self.cosa_run(custom_args)
                    
                elif command == 'shell':
                    print("🐚 Opening COSA shell...")
                    self.run_cosa_command("shell")
                    
                elif command == 'disk':
                    self.check_disk_space()
                    
                elif command == 'clean':
                    self.clean_builds()
                    
                elif command == 'clean-all':
                    self.clean_builds()
                    self.clean_containers()
                    
                elif command == 'clean-dir':
                    self.clean_directory()
                    
                elif command == 'kola_help':
                    print("🧪 Kola Testing Commands:")
                    print("   kola list        - List all available tests")
                    print("   kola run [pattern] - Run tests (all or matching pattern)")
                    print("   kola interactive - Interactive test selection")
                    print("   test [pattern]   - Shorthand for kola run")
                    print("   test-summary     - Show testing status")
                    
                elif command == 'kola_list':
                    self.kola_list_tests()
                    
                elif command == 'kola_run':
                    if args:
                        pattern = " ".join(args)
                        self.kola_run_tests(pattern)
                    else:
                        # Ask user what they want to test
                        print("🧪 Kola Test Options:")
                        print("   1. Run all tests (press Enter)")
                        print("   2. List tests first (type 'list')")
                        print("   3. Interactive selection (type 'interactive')")
                        choice = input("Choose option: ").strip().lower()
                        
                        if choice == 'list':
                            self.kola_list_tests()
                        elif choice == 'interactive':
                            self.kola_run_specific_tests()
                        else:
                            self.kola_run_tests()
                            
                elif command == 'kola_interactive':
                    self.kola_run_specific_tests()
                    
                elif command == 'test_summary':
                    self.show_test_summary()
                    
                else:
                    print(f"❌ Unknown command: {command}")
                    print("   Try 'build rawhide', 'build stable', or 'build testing-devel'")
                    print("   After building, try 'kola list', 'run basic test', or 'run podman test'")
                    print("   Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fedora CoreOS Assembler Chatbot')
    parser.add_argument('--work-dir', default='./fcos', 
                       help='Working directory for COSA (default: ./fcos)')
    parser.add_argument('--build', metavar='STREAM',
                       help='Automatically build specified stream (e.g., rawhide, stable, testing-devel)')
    parser.add_argument('--config-repo', 
                       help='Custom config repository URL')
    
    args = parser.parse_args()
    
    # Create bot instance
    bot = FedoraCOSABot(args.work_dir)
    if args.config_repo:
        bot.config_repo = args.config_repo
    
    if args.build:
        print(f"🤖 Running automated build for stream: {args.build}")
        
        if not bot.check_prerequisites():
            sys.exit(1)
            
        # Pull container
        if not bot.pull_container():
            sys.exit(1)
            
        # Build specified stream
        if bot.build_stream(args.build):
            print(f"🎉 Successfully built Fedora CoreOS {args.build}!")
        else:
            print(f"❌ Failed to build {args.build}")
            sys.exit(1)
    else:
        # Interactive mode
        bot.interactive_mode()

if __name__ == '__main__':
    main()