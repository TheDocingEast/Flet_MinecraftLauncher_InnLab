# InnLab³ Minecraft Launcher

# WARNING, README and CHANGELOG was wrote by AI, don't believe them. The project at the prototype stage, most of the functions was realized by AI and very unstable, checking human security and performance in the process

A modern, feature-rich Minecraft launcher built with Python and Flet, designed for managing modpacks and providing a seamless gaming experience.

## Features

### 🎮 Core Functionality
- **Automatic Updates**: Built-in update system for modpacks and launcher
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Java Detection**: Automatic Java installation detection and validation
- **Memory Management**: Configurable RAM allocation with system detection
- **Skin Support**: Custom skin loading and management

### 🎨 User Interface
- **Modern Dark Theme**: Sleek purple-themed dark interface
- **Responsive Design**: Adaptive layout that works on different screen sizes
- **Intuitive Navigation**: Easy-to-use card-based modpack selection
- **Real-time Configuration**: Live settings updates without restart

### 🔧 Technical Features
- **Enhanced Error Handling**: Comprehensive logging and error recovery
- **Configuration Management**: Robust config validation and backup
- **Backup System**: Automatic backups before updates
- **Performance Optimized**: Efficient resource usage and fast startup

## Installation

### Prerequisites
- Python 3.8 or higher
- Java 8 or higher (for Minecraft)
- At least 4GB RAM (8GB+ recommended)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd VCS_testflet
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the launcher**:
   ```bash
   python src/main.py
   ```

### Building Executable

To create a standalone executable:

```bash
# Windows
build_launcher.bat

# Linux/macOS
chmod +x build_launcher.sh
./build_launcher.sh
```

## Configuration

The launcher uses a `config.json` file for settings:

```json
{
  "ram": 8,
  "skin": "path/to/skin.png",
  "nickname": "YourUsername",
  "theme": "dark",
  "auto_update": true,
  "java_path": "",
  "window_width": 1200,
  "window_height": 800
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ram` | number | 4 | RAM allocation in GB (2-32) |
| `skin` | string | "" | Path to custom skin file |
| `nickname` | string | "Player" | In-game username |
| `theme` | string | "dark" | UI theme (dark/light) |
| `auto_update` | boolean | true | Enable automatic updates |
| `java_path` | string | "" | Custom Java executable path |
| `window_width` | number | 1200 | Launcher window width |
| `window_height` | number | 800 | Launcher window height |

## Project Structure

```
VCS_testflet/
├── src/
│   ├── main.py          # Main application entry point
│   ├── launcher.py      # Minecraft launcher logic
│   ├── updater.py       # Update management system
│   ├── utils.py         # Utility functions
│   └── assets/          # UI assets (images, icons)
├── dist/                # Built executables
├── minecraft/           # Minecraft installation directory
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
└── build_launcher.bat   # Build script
```

## Development

### Code Architecture

The launcher follows a modular architecture:

- **ConfigManager**: Handles configuration loading, validation, and saving
- **ModpackCard**: Manages individual modpack display and interaction
- **MinecraftLauncher**: Core Minecraft launching functionality
- **UpdateManager**: Handles update checking and installation
- **Utility Functions**: Cross-platform system operations

### Key Improvements Made

1. **Enhanced Error Handling**: Comprehensive try-catch blocks with logging
2. **Type Hints**: Full type annotation for better code maintainability
3. **Cross-Platform Support**: Works on Windows, macOS, and Linux
4. **Configuration Validation**: Robust input validation and sanitization
5. **Logging System**: Detailed logging for debugging and monitoring
6. **Memory Management**: Smart RAM detection and allocation
7. **Backup System**: Automatic backups before critical operations
8. **Update System**: Complete update management with progress tracking

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with proper error handling and logging
4. Add tests if applicable
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Include comprehensive docstrings
- Add proper error handling with logging
- Maintain backward compatibility where possible

## Troubleshooting

### Common Issues

**Java Not Found**:
- Install Java 8 or higher
- Set `java_path` in config.json to custom Java location

**Memory Issues**:
- Reduce RAM allocation in settings
- Close other applications before launching
- Ensure sufficient system memory

**Update Failures**:
- Check internet connection
- Verify update server accessibility
- Check disk space for downloads

**Skin Loading Issues**:
- Ensure skin file is valid PNG format
- Check file permissions
- Verify skin file path in config

### Logs

Check these log files for debugging:
- `launcher.log` - Main application logs
- `minecraft_launcher.log` - Minecraft-specific logs
- `minecraft_latest.log` - Game output logs

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Flet](https://flet.dev/) for the modern UI framework
- Uses [minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib) for Minecraft integration
- Inspired by the need for a better modpack management experience

## Support

For support, please:
1. Check the troubleshooting section
2. Review the logs for error details
3. Create an issue with detailed information
4. Include system information and log excerpts

---

**Version**: 2.0.0  
**Last Updated**: 2024  
**Compatibility**: Python 3.8+, Windows/macOS/Linux