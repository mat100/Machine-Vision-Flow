# Data Directory

This directory is used for runtime data storage.

## Purpose
- Runtime storage for application data
- Not tracked in git (temporary/generated files only)

## Usage
Application components may use this directory for:
- Temporary file storage
- Runtime cache
- Generated data files

**Note:** This directory should remain empty in the repository. All files created here are considered temporary and should not be committed to version control.
