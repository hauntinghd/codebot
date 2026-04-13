# CodeBot User Guide

Welcome to CodeBot! This guide will help you get started and make the most of your coding assistant.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [File Uploads](#file-uploads)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)
6. [Subscription Plans](#subscription-plans)

## Getting Started

### Creating an Account

1. Visit the CodeBot dashboard
2. Click "Sign in with Google" to authenticate with your Google account
3. You'll be automatically logged in and can start using CodeBot immediately

### Understanding Credits

- Credits are allocated monthly based on your subscription plan
- Each API call consumes credits based on the model used and tokens processed
- Credits reset monthly on your billing date
- Check your remaining credits in the sidebar

## Basic Usage

### Starting a Chat

1. Once logged in, you'll see the CodeBot interface
2. Type your question or request in the message box
3. Click the send button or press Enter to submit
4. CodeBot will analyze your request and provide code solutions

### Example Requests

**Building from Scratch:**
```
"Create a Python Flask API with endpoints for users and posts"
```

**Fixing Errors:**
```
"I'm getting this error: [paste error message]. Here's my code: [paste code]"
```

**Refactoring:**
```
"Refactor this code to use async/await: [paste code]"
```

### Code Preview

- When CodeBot generates code blocks, you'll see a "Preview" button
- Click it to view the code in a formatted preview panel
- This helps you review code before using it

## File Uploads

### Supported File Types

- **ZIP files**: Upload entire projects as ZIP archives
- **MP4 files**: Upload video files for analysis
- **PNG/WebP images**: Upload up to 20 images per account

### Uploading Files

1. Click the upload button (📤) next to the message input
2. Select the file(s) you want to upload
3. Wait for the upload confirmation
4. Mention "zip", "upload", or "file" in your message to reference uploaded files

### ZIP File Analysis

When you upload a ZIP file and mention it in your message:
- CodeBot automatically extracts and analyzes the contents
- Important files (README, config files, main code) are prioritized
- Large codebases are intelligently sampled to stay within limits
- Binary files and unnecessary directories are excluded

## Best Practices

### Getting Better Results

1. **Be Specific**: Provide clear, detailed requests
   - ✅ "Fix the authentication bug in login.py that causes 500 errors"
   - ❌ "Fix my code"

2. **Include Context**: Share relevant code, error messages, and requirements
   - Include error stack traces
   - Mention your tech stack (Python, JavaScript, etc.)
   - Specify any constraints or requirements

3. **Break Down Complex Tasks**: For large projects, ask about specific files or features
   - "Analyze the database schema in models.py"
   - "Review the API routes in routes.py"

4. **Use Preview Feature**: Always preview generated code before implementing
   - Check for syntax errors
   - Verify the logic matches your requirements
   - Test in a safe environment first

### Code Quality Tips

- **Review Generated Code**: Always review and test code before deploying
- **Test Incrementally**: Test small changes before moving to larger refactors
- **Version Control**: Use Git to track changes and revert if needed
- **Security**: Review code for security vulnerabilities, especially authentication and data handling

## Troubleshooting

### Common Issues

**"Subscription Required" Message**
- Ensure you have an active subscription
- Check your plan status in the profile menu
- Upgrade your plan if needed

**"Rate Limit Exceeded"**
- You've made too many requests in a short time
- Wait a moment and try again
- Consider breaking large requests into smaller ones

**"Insufficient Credits"**
- Check your remaining credits in the sidebar
- Upgrade your plan for more credits
- Credits reset monthly on your billing date

**Large ZIP Files Not Processing**
- Very large codebases may exceed token limits
- Try asking about specific files instead of the entire codebase
- Split large projects into smaller ZIP files

**Code Not Working as Expected**
- Review the generated code carefully
- Check for missing dependencies or imports
- Verify the code matches your requirements
- Ask follow-up questions for clarification

### Getting Help

- Review error messages carefully - they often contain helpful information
- Try rephrasing your request if you're not getting the desired result
- Break complex requests into smaller, more specific questions
- Use the preview feature to review code before implementing

## Subscription Plans

### Basic Plan ($50/month)
- $45 in monthly credits
- Suitable for individual developers
- Good for small to medium projects

### Pro Plan ($250/month)
- $225 in monthly credits
- Ideal for professional developers and teams
- Handles larger codebases and more frequent usage

### Managing Your Subscription

- **Upgrade**: Click the profile menu (☰) → "Upgrade Plan"
- **Billing**: Click "Billing Portal" to manage payment methods and view invoices
- **Cancel**: Cancel anytime through the billing portal (no cancellation fees)

## Tips for Maximum Value

1. **Plan Your Requests**: Think about what you need before asking
2. **Use Context Efficiently**: Upload relevant files, not entire repositories unless necessary
3. **Iterate**: Start with basic requests, then refine based on results
4. **Learn Patterns**: Notice what request styles work best for your use case

## Security Reminders

- Never share API keys, passwords, or sensitive credentials in chats
- Review generated code for security vulnerabilities
- Use CodeBot in a secure environment
- Keep your account credentials secure

---

**Need More Help?**

If you encounter issues not covered in this guide, please contact support through your account dashboard.

Happy coding with CodeBot! 🚀

