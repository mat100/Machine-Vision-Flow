# Contributing to Machine Vision Flow

Thank you for your interest in contributing to Machine Vision Flow! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Requests](#pull-requests)
- [Code Review Process](#code-review-process)

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+ and npm
- Git

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/MachineVisionFlow.git
   cd MachineVisionFlow
   ```

2. **Install dependencies:**
   ```bash
   make install
   ```

   **Note:** This installs development dependencies. For production, use:
   ```bash
   cd python-backend
   pip install -r requirements.txt
   ```

3. **Set up pre-commit hooks:**
   ```bash
   make setup-hooks
   ```

4. **Run tests to verify setup:**
   ```bash
   make test
   ```

### Dependency Management

The project uses separate requirement files:

- **`requirements.txt`** - Production dependencies only (pinned versions)
- **`requirements-dev.txt`** - Development dependencies (testing, linting, etc.)

**Installing dependencies:**
```bash
# Development (includes production + dev tools)
pip install -r requirements-dev.txt

# Production only
pip install -r requirements.txt
```

**Adding new dependencies:**
1. Add to appropriate file with pinned version
2. Run `pip install -r requirements-dev.txt` to install
3. Test thoroughly
4. Commit both requirement files

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Develop using VSCode (recommended):**
   ```bash
   # Open in VSCode and press F5
   # Select "Debug: Full Stack (Python + Node-RED)"
   # Set breakpoints and debug your changes
   ```

   Or use production mode:
   ```bash
   make start  # Start services
   make logs   # View logs
   ```

3. **Make your changes**
   - Write code following our [code style](#code-style)
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and linting:**
   ```bash
   make test
   make lint
   make format
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

   **Commit Message Format:**
   ```
   <type>: <subject>

   <body>

   <footer>
   ```

   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

   Example:
   ```
   feat: Add blob detection algorithm

   Implements blob detection using SimpleBlobDetector from OpenCV.
   Includes configurable parameters for area, circularity, and convexity.

   Closes #123
   ```

5. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**

## Code Style

### Python

We follow [PEP 8](https://peps.python.org/pep-0008/) with the following tools:

- **black** - Code formatting (line length: 100)
- **isort** - Import sorting
- **flake8** - Linting

**Auto-format your code:**
```bash
make format
```

**Check for issues:**
```bash
make lint
```

### Code Guidelines

1. **Type Hints:** Use type hints for function arguments and return values
   ```python
   def process_image(image: np.ndarray, threshold: float = 0.8) -> dict:
       ...
   ```

2. **Docstrings:** Use docstrings for modules, classes, and functions
   ```python
   def template_match(image: np.ndarray, template: np.ndarray) -> dict:
       """
       Perform template matching on the input image.

       Args:
           image: Input image as numpy array
           template: Template image to match

       Returns:
           Dictionary containing match results with score and position
       """
   ```

3. **Error Handling:** Use custom exceptions and proper error messages
   ```python
   if not image_exists(image_id):
       raise ImageNotFoundException(f"Image {image_id} not found")
   ```

4. **Logging:** Use structured logging
   ```python
   logger.info(f"Processing image {image_id}")
   logger.error(f"Failed to process image: {error}")
   ```

### Node-RED Nodes

- Follow Node-RED coding standards
- Include comprehensive help text in HTML files
- Add input validation
- Handle errors gracefully

### JavaScript/HTML

- Use consistent indentation (2 spaces)
- Follow Node-RED UI conventions
- Document node properties

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
cd python-backend
pytest tests/test_specific.py -v

# Run specific test
pytest tests/test_specific.py::test_function_name -v
```

### Writing Tests

1. **Test Coverage:** Aim for >80% code coverage
2. **Test Structure:** Use AAA pattern (Arrange, Act, Assert)
   ```python
   def test_template_match_basic():
       # Arrange
       image = create_test_image()
       template = create_test_template()

       # Act
       result = template_match(image, template)

       # Assert
       assert result["found"] == True
       assert result["score"] > 0.8
   ```

3. **Fixtures:** Use pytest fixtures for common setup
4. **Mocking:** Mock external dependencies (cameras, file I/O)

### Test Requirements

- All new features must include tests
- Bug fixes should include regression tests
- Tests must pass before merging

## Pull Requests

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Code follows style guidelines
```

### PR Size

- Keep PRs focused and reasonably sized
- Large features should be split into multiple PRs
- Each PR should be reviewable in 30 minutes or less

## Code Review Process

### For Contributors

1. **Address feedback promptly**
2. **Be open to suggestions**
3. **Ask questions if unclear**
4. **Update PR based on feedback**

### Review Criteria

Code reviews check for:

- Correctness and functionality
- Code quality and maintainability
- Test coverage
- Documentation
- Performance implications
- Security considerations

### Approval Process

- At least 1 approval required
- All CI checks must pass
- No unresolved conversations

## Development Tips

### Useful Commands

```bash
make help           # Show all available commands
make dev            # Start development mode
make reload         # Restart services
make logs           # View logs
make clean          # Clean runtime files
make clean --all    # Clean everything
```

### Debugging

1. **Python Backend:**
   ```bash
   cd python-backend
   source venv/bin/activate
   python main.py  # Run directly for debugging
   ```

2. **Check API:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **View Logs:**
   ```bash
   make logs
   # or
   tail -f var/log/backend.log
   tail -f var/log/node-red.log
   ```

### Common Issues

- **Port already in use:** `make stop` then `make start`
- **Tests failing:** Check if services are running: `make stop`
- **Import errors:** Reinstall dependencies: `make install`

## Questions?

- Check existing [Issues](https://github.com/your-org/MachineVisionFlow/issues)
- Read the [Documentation](docs/)
- Ask in [Discussions](https://github.com/your-org/MachineVisionFlow/discussions)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Machine Vision Flow! 🎉
