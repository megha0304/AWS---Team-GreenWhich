#!/bin/bash

# Bash script to commit and push all changes

echo "🚀 CloudForge Bug Intelligence - Git Commit & Push"
echo "================================================="
echo ""

# Show current status
echo "📊 Current Git Status:"
git status --short
echo ""

# Add all changes
echo "➕ Adding all changes..."
git add .

# Show what will be committed
echo ""
echo "📝 Files to be committed:"
git status --short
echo ""

# Commit with message
echo "💾 Creating commit..."
git commit -F COMMIT_MESSAGE.txt

# Show commit info
echo ""
echo "✅ Commit created successfully!"
git log -1 --oneline
echo ""

# Ask before pushing
echo "🔄 Ready to push to origin/main?"
read -p "Press Enter to push, or Ctrl+C to cancel"

# Push to remote
echo ""
echo "⬆️  Pushing to remote..."
git push origin main

echo ""
echo "🎉 Successfully pushed to remote!"
echo ""
echo "📚 Next Steps:"
echo "1. Open AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md"
echo "2. Follow the 5-part setup guide"
echo "3. Get your permanent shareable link!"
echo ""
