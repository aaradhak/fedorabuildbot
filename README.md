# Fedora CoreOS Assembler (COSA) Chatbot

This project introduces a Python bot designed to **automate Fedora CoreOS (FCOS) image builds and Kola test reproduction**.

The goal is to simplify the process of:
* Building specific FCOS streams (e.g., `rawhide`, `stable`).
* Running Kola tests to reproduce and debug issues from pipeline failures.

## 🚀 What it Does (So Far)

* Automates `cosa init`, `fetch`, and `build` for FCOS streams.
* Provides commands to list and run Kola tests.
* Includes basic utilities for disk space checks and cleanup.

## 💡 Why This Project?

Manually reproducing FCOS build and test failures can be time-consuming. This bot aims to automate those steps, making debugging faster and more efficient.

## ⚙️ Get Started

For detailed instructions on how to set up and run the bot, please see the [RUNNING_THE_BOT.md](RUNNING_THE_BOT.md) file.
