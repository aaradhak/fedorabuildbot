Here's a README.md and a separate `RUNNING_THE_BOT.md` document for your GitHub repository, based on the `fedorabot.py` file you provided.

-----

## README.md

```markdown
# Fedora CoreOS Assembler (COSA) Chatbot

An intelligent chatbot designed to **automate the process of building Fedora CoreOS (FCOS) streams and reproducing Kola test failures**. This bot simplifies complex COSA (CoreOS Assembler) commands, allowing users to easily build specific FCOS architectures and versions, and then efficiently run Kola tests to identify and debug issues directly from pipeline failures.

Whether you're a developer needing to quickly replicate a bug, a QA engineer verifying a fix, or simply want to explore different FCOS streams, this bot streamlines your workflow.

## 🚀 Features

* **Automated Stream Builds:** Easily build `stable`, `testing`, `testing-devel`, `next`, or `rawhide` Fedora CoreOS streams with a single command.
* **Kola Test Automation:**
    * List all available Kola tests.
    * Run specific tests, multiple tests, or all tests using patterns.
    * Interactive test selection for guided execution.
    * Provides quick commands for common tests (e.g., `run basic test`, `run podman test`).
* **Intelligent Workflow:** Automatically handles `cosa init`, `fetch`, and `build` steps for chosen streams.
* **Stream Management:** Easily switch between different FCOS streams (branches) and keep track of their build status.
* **Prerequisite Checks:** Verifies `podman` and `git` availability, and warns about `KVM` status.
* **Resource Management:** Includes commands to check disk space and clean old builds or containers.
* **User-Friendly Interface:** Natural language command parsing for intuitive interactions.

## 💡 Why This Bot?

Reproducing Fedora CoreOS test failures manually can be a tedious and time-consuming process, involving:
1.  Manually checking the failed pipeline's logs to identify the FCOS stream and architecture.
2.  Setting up a development environment with COSA.
3.  Manually initializing COSA and cloning the `fedora-coreos-config` repository.
4.  Switching to the correct branch corresponding to the failed stream.
5.  Running `cosa fetch` to pull metadata and packages.
6.  Running `cosa build` to create the VM image.
7.  Finally, executing the specific Kola test that failed.

This bot automates these steps, allowing you to go from a failed pipeline to **reproducing the failure in a locally built VM with a few simple commands.** This significantly reduces debugging time and improves developer efficiency.

## ⚙️ How to Use

For detailed instructions on setting up and running the bot, please refer to the [RUNNING_THE_BOT.md](RUNNING_THE_BOT.md) document.

## 🤝 Contributing

Contributions are welcome! If you have suggestions for new features, improvements, or bug fixes, feel free to open an issue or submit a pull request.

## 📜 License

[Specify your license here, e.g., MIT, Apache 2.0, etc.]
```

-----

## RUNNING\_THE\_BOT.md

````markdown
# Running the Fedora CoreOS Assembler (COSA) Chatbot

This document provides detailed instructions on how to set up, run, and interact with the Fedora CoreOS Assembler Chatbot.

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Podman:** The bot uses Podman to run the CoreOS Assembler (COSA) container.
    * Installation instructions: [https://podman.io/docs/installation](https://podman.io/docs/installation)
2.  **Git:** Required for cloning the `fedora-coreos-config` repository.
    * Installation instructions: [https://git-scm.com/book/en/v2/Getting-Started-Installing-Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
3.  **Python 3:** The bot is written in Python 3.
    * Most Linux distributions come with Python 3 pre-installed. You can check your version with `python3 --version`.

### KVM (Kernel-based Virtual Machine)

The bot will warn you if `/dev/kvm` is not found. While the bot can still run COSA commands, **virtualization for running built VMs or Kola tests will not work without KVM enabled.** Ensure KVM is properly set up on your system for full functionality.

* **Linux:**
    ```bash
    ls -l /dev/kvm
    ```
    If it's not present or you don't have permissions, you might need to:
    * Install `qemu-kvm` or `libvirt-daemon` (package names vary by distribution).
    * Add your user to the `kvm` group: `sudo usermod -a -G kvm $USER` (then log out and back in).

## 🚀 Getting Started

1.  **Clone the Repository:**
    First, clone the GitHub repository containing the `fedorabot.py` file:

    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME
    ```
    (Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub details.)

2.  **Run the Bot:**

    You can run the bot in two primary modes:

    ### A. Interactive Mode (Recommended for general use)

    This mode provides a conversational interface where you can issue commands.

    ```bash
    python3 fedorabot.py
    ```

    Upon starting, the bot will perform prerequisite checks and welcome you.

    ### B. Direct Build Mode (For quick, non-interactive builds)

    You can directly trigger a build for a specific stream from the command line.

    ```bash
    python3 fedorabot.py --build rawhide
    ```
    Replace `rawhide` with your desired stream (e.g., `stable`, `testing`, `testing-devel`, `next`). This mode will automatically initialize COSA (if not already), pull the container, fetch packages, and build the specified image.

    You can also specify a custom working directory:
    ```bash
    python3 fedorabot.py --work-dir /path/to/your/fcos_builds --build stable
    ```

## 🤖 Bot Commands and Usage

Once the bot is running in interactive mode, you can use the following commands.

### Quick Build & Test Examples:

* **Build the latest development version:**
    ```
    build rawhide
    ```
* **Build the stable release:**
    ```
    build stable
    ```
* **Build the testing development version:**
    ```
    build testing-devel
    ```
* **List all available Kola tests after a build:**
    ```
    kola list
    ```
* **Run basic Kola tests (natural language):**
    ```
    run basic test
    ```
    or simply:
    ```
    run basic
    ```
* **Run Podman-related Kola tests:**
    ```
    run podman test
    ```
* **Interactively select and run Kola tests:**
    ```
    kola interactive
    ```
* **Start the built CoreOS VM:**
    ```
    run
    ```
    (Note: `run` without a test pattern will start the VM. With a test pattern, it runs Kola tests.)

### General Commands:

* `help`: Displays a list of all available commands and their descriptions.
* `status`: Shows the current build status, working directory, initialized state, current stream, and build states for different streams. Also checks disk space.
* `quit` / `exit`: Exits the bot.

### Initialization & Configuration:

* `init [repo_url]`: Initializes COSA. This clones the `fedora-coreos-config` repository into your working directory. If `repo_url` is not provided, it defaults to `https://github.com/coreos/fedora-coreos-config`.
    * **Important:** COSA `init` works best in an empty directory. If your working directory is not empty, the bot will warn you.
* `force-init [repo_url]`: Forces COSA initialization, even if the working directory is not empty. Use with caution as it might overwrite existing files.
* `pull`: Pulls the latest COSA container image (`quay.io/coreos-assembler/coreos-assembler:latest`).

### Stream Management:

* `streams` / `list_streams`: Lists all available Fedora CoreOS streams (branches) from the configured repository.
* `refresh`: Fetches all remote branches from the configuration repository and updates the list of available streams. Useful if new streams are added upstream.
* `switch <stream_name>`: Switches the local COSA configuration to the specified stream/branch (e.g., `switch rawhide`).
* `current`: Shows the currently active Fedora CoreOS stream.

### Build Commands:

* `fetch [stream_name]`: Fetches metadata and packages for the current or specified stream.
* `build [stream_name]`: Builds the CoreOS image for the current or specified stream. This will also automatically run `fetch` if not already done for the stream.
* `build <stream_name>`: (Alias for `build_stream`) This is the main automated command that handles `init` (if needed), `switch`, `fetch`, and `build` in one go for the specified stream.

### Kola Testing Commands:

* `kola list`: Lists all available Kola tests for the currently built stream.
* `kola run [test_pattern] [custom_args]`: Runs Kola tests.
    * If no `test_pattern` is given, it attempts to run all tests.
    * You can specify a `test_pattern` (e.g., `basic`, `podman.*`, `basic.sanity`) to run specific tests or groups of tests.
    * `custom_args` allows you to pass additional arguments directly to Kola (e.g., `--parallel=4`, `--qemu-image=/path/to/image.qcow2`).
* `test [test_pattern]`: Shorthand for `kola run [test_pattern]`.
* `kola interactive`: Provides an interactive prompt to help you select and run specific Kola tests with optional arguments.
* `test-summary`: Shows a summary of which streams have been built and are ready for testing.

### Utility & Maintenance:

* `run [custom_args]`: Runs the built Fedora CoreOS VM. You can pass QEMU-specific `custom_args` here (e.g., `run -m 4G`).
* `shell`: Opens an interactive shell inside the COSA container, allowing you to run `cosa` commands directly.
* `disk`: Checks the available disk space in the working directory. FCOS builds require significant space (10-20 GB).
* `clean`: Cleans old build artifacts in the `builds` directory, keeping only the latest.
* `clean-all`: Performs `clean` and also prunes unused Podman containers and images to free up more space.
* `clean-dir`: **WARNING:** This command will **delete all contents** of your working directory (`./fcos` by default). Use with extreme caution. It's useful if you want to start fresh.

## 📁 Working Directory Structure

By default, the bot operates within a `./fcos` directory relative to where you run the script. This directory will contain:

* `src/config`: Cloned `fedora-coreos-config` repository.
* `cache`: COSA's cache directory.
* `builds`: Contains the built FCOS images for different streams.

You can change this working directory using the `--work-dir` argument when starting the bot.

````

```
```
