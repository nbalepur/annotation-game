#!/bin/bash

export SAGEMAKER_CONFIG_LOG_LEVEL=ERROR

# Define the backup repository path (CHANGE THIS TO YOUR DESIRED BACKUP LOCATION)
BACKUP_REPO="/Users/nishantbalepur/Desktop/Repositories/annotation-game/backup"

# Create a timestamped folder for the backup
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="$BACKUP_REPO/$TIMESTAMP"

# Ensure the backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Backing up data to $BACKUP_DIR ..."

# Run the dumpdata commands and save JSON files in the backup directory
python manage.py dumpdata game.User --indent 2 | tail -n +3 > "$BACKUP_DIR/game_user.json"
python manage.py dumpdata auth.User --indent 2 | tail -n +3 > "$BACKUP_DIR/auth_user.json"
python manage.py dumpdata game.Document --indent 2 | tail -n +3 > "$BACKUP_DIR/document.json"
python manage.py dumpdata game.AnswerData --indent 2 | tail -n +3 > "$BACKUP_DIR/answer_data.json"
python manage.py dumpdata game.LeaderboardLog --indent 2 | tail -n +3 > "$BACKUP_DIR/leaderboard_log.json"
python manage.py dumpdata game.ToolLog --indent 2 | tail -n +3 > "$BACKUP_DIR/tool_log.json"
python manage.py dumpdata game.ComparisonFeedback --indent 2 | tail -n +3 > "$BACKUP_DIR/comparison_feedback.json"
python manage.py dumpdata game.ReportIssue --indent 2 | tail -n +3 > "$BACKUP_DIR/report_issue.json"

# Compress the backup folder and remove the other files
tar -czf "$BACKUP_REPO/$TIMESTAMP.tar.gz" -C "$BACKUP_REPO" "$TIMESTAMP"
rm -rf "$BACKUP_DIR"

echo "Backup completed successfully!"
