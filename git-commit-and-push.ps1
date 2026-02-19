# PowerShell script to commit and push all changes

Write-Host "🚀 CloudForge Bug Intelligence - Git Commit & Push" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Show current status
Write-Host "📊 Current Git Status:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Add all changes
Write-Host "➕ Adding all changes..." -ForegroundColor Green
git add .

# Show what will be committed
Write-Host ""
Write-Host "📝 Files to be committed:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Commit with message
Write-Host "💾 Creating commit..." -ForegroundColor Green
git commit -F COMMIT_MESSAGE.txt

# Show commit info
Write-Host ""
Write-Host "✅ Commit created successfully!" -ForegroundColor Green
git log -1 --oneline
Write-Host ""

# Ask before pushing
Write-Host "🔄 Ready to push to origin/main?" -ForegroundColor Yellow
$response = Read-Host "Press Enter to push, or Ctrl+C to cancel"

# Push to remote
Write-Host ""
Write-Host "⬆️  Pushing to remote..." -ForegroundColor Green
git push origin main

Write-Host ""
Write-Host "🎉 Successfully pushed to remote!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Open AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md" -ForegroundColor White
Write-Host "2. Follow the 5-part setup guide" -ForegroundColor White
Write-Host "3. Get your permanent shareable link!" -ForegroundColor White
Write-Host ""
