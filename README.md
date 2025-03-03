# Hyperliquid Tracking Leaderboard

This repository contains a Python-based tracking leaderboard bot designed to monitor and report trading positions on the Hyperliquid platform. The bot fetches trading data from the Hyperliquid API, processes it, and sends notifications via Telegram. It is particularly useful for tracking the positions of specific user addresses and receiving real-time updates on new or closed positions.

## Features

- **Real-time Position Monitoring**: Tracks trading positions for specified user addresses.
- **Telegram Notifications**: Sends alerts for new positions opened, positions closed, and current positions.
- **Customizable User Addresses**: Allows monitoring of multiple user addresses.
- **Detailed Position Information**: Provides details such as entry price, leverage, estimated entry size, and unrealized PnL.

## Prerequisites

Before running the bot, ensure you have the following:

- Python 3.x installed.
- A Telegram bot token and chat ID for notifications.
- User addresses to monitor on the Hyperliquid platform.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/hyperliquid-bot.git
   cd hyperliquid-bot
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Configuration**:
   Run the setup script to configure your Telegram bot token, chat ID, and user addresses:
   ```bash
   python setup.py
   ```
   Follow the prompts to input your Telegram bot token, chat ID, and the user addresses you wish to monitor.

## Usage

1. **Run the Bot**:
   Start the bot by running the main script:
   ```bash
   python main.py
   ```

2. **Monitor Logs**:
   The bot will log its activities to `bot.log` and print logs to the console. It will also send notifications to the specified Telegram chat.

3. **Customize Monitoring**:
   To add or remove user addresses, edit the `user_addresses.json` file or rerun the setup script.

## File Structure

- **`hyperliquid.py`**: Contains functions to interact with the Hyperliquid API, fetching mark prices, positions, and leaderboard information.
- **`main.py`**: The main script that runs the bot, processes data, and sends Telegram notifications.
- **`message.py`**: Handles sending messages to Telegram.
- **`misc.py`**: Provides utility functions for HTTP headers and JSON payloads.
- **`setup.py`**: Initial setup script for configuring the bot.
- **`requirements.txt`**: Lists the Python dependencies required for the bot.
- **`config.ini`**: Stores the Telegram bot token and chat ID.
- **`user_addresses.json`**: Contains the list of user addresses to monitor.

## Configuration

- **Telegram Configuration**: Edit `config.ini` to update the Telegram bot token and chat ID.
- **User Addresses**: Edit `user_addresses.json` to add or remove user addresses.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For any issues or questions, please open an issue on the GitHub repository or contact the maintainers directly.

---

This README provides a comprehensive guide to setting up and using the Hyperliquid Tracking Leaderboard. For further customization or advanced usage, refer to the individual script documentation and comments within the code.
