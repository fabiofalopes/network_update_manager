# Icons for SIGES Updater

Place your custom icons in this directory to be used by the application.

## Available Icon Options

You can add the following icons:

- `updater.ico` - The main application icon
- `idle.ico` - Icon shown when the updater is idle
- `checking.ico` - Icon shown when checking for updates 
- `downloading.ico` - Icon shown when downloading updates
- `completed.ico` - Icon shown when updates are complete
- `error.ico` - Icon shown when an error occurs

## Configuration

The paths to these icons can be configured in the `.env` file:

```
TRAY_ICON_PATH=app/icons/updater.ico
STATUS_ICON_IDLE=app/icons/idle.ico
STATUS_ICON_CHECKING=app/icons/checking.ico
STATUS_ICON_DOWNLOADING=app/icons/downloading.ico
STATUS_ICON_COMPLETED=app/icons/completed.ico
STATUS_ICON_ERROR=app/icons/error.ico
```

## Fallback Behavior

If any of these icons are missing, the application will create simple colored circles:
- Idle: Gray
- Checking: Blue
- Downloading: Yellow 
- Completed: Green
- Error: Red 