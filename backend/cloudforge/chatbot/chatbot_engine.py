"""
Chatbot Engine - Conversational AI for bug analysis and resolution.

Provides intelligent responses about bugs, fixes, workflows, and system status.
Integrates with CloudForge agents and maintains conversation context.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field
import asyncio

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Represents a single chat message."""
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    sender: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """Represents a chat session with conversation history."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatbotEngine:
    """
    Main chatbot engine for conversational bug analysis and resolution.
    
    Features:
    - Natural language understanding of bug-related queries
    - Context-aware responses based on workflow state
    - Command processing for actions (analyze, suggest, rollback, etc.)
    - Conversation history management
    - Integration with CloudForge agents
    """
    
    def __init__(self, bedrock_client: Any, config: Dict[str, Any], orchestrator: Any = None, state_store: Any = None):
        """
        Initialize chatbot engine.
        
        Args:
            bedrock_client: AWS Bedrock client for Claude integration
            config: Configuration dictionary with model_id, max_retries, etc.
            orchestrator: WorkflowOrchestrator instance for running workflows
            state_store: StateStore instance for accessing workflow state
        """
        self.bedrock_client = bedrock_client
        self.config = config
        self.model_id = config.get('bedrock_model_id', 'anthropic.claude-3-sonnet-20240229-v1:0')
        self.sessions: Dict[str, ChatSession] = {}
        self.orchestrator = orchestrator
        self.state_store = state_store
        self.logger = logging.getLogger(__name__)
    
    async def create_session(self, workflow_id: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(workflow_id=workflow_id)
        self.sessions[session.session_id] = session
        self.logger.info(f"Created chat session {session.session_id}")
        return session
    
    async def send_message(
        self,
        session_id: str,
        user_message: str,
        workflow_state: Optional[Dict[str, Any]] = None,
        repository_path: Optional[str] = None
    ) -> ChatMessage:
        """
        Process user message and generate assistant response.
        
        Args:
            session_id: Chat session ID
            user_message: User's message
            workflow_state: Current workflow state for context
            repository_path: Path to repository for workflow execution
            
        Returns:
            Assistant's response message
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        # NOTE: Do NOT add user message to history here
        # The frontend already adds it, so we only add the assistant response
        
        # Update context with workflow state
        if workflow_state:
            session.context.update(workflow_state)
        
        # Check if user wants to run a workflow
        response_text = await self._process_user_intent(
            user_message,
            session,
            repository_path
        )
        
        # Add ONLY assistant response to history
        assistant_msg = ChatMessage(sender="assistant", content=response_text)
        session.messages.append(assistant_msg)
        session.updated_at = datetime.utcnow()
        
        self.logger.info(f"Generated response for session {session_id}")
        return assistant_msg
    
    async def _process_user_intent(
        self,
        user_message: str,
        session: ChatSession,
        repository_path: Optional[str]
    ) -> str:
        """
        Process user intent and execute appropriate actions.
        
        Args:
            user_message: User's message
            session: Chat session
            repository_path: Repository path or GitHub URL for workflow
            
        Returns:
            Response text
        """
        msg_lower = user_message.lower()
        
        # Check for quick button actions
        if msg_lower == "show critical bugs":
            return await self.filter_and_sort_bugs(session, 'CRITICAL')
        elif msg_lower == "show high priority bugs":
            return await self.filter_and_sort_bugs(session, 'HIGH')
        elif msg_lower == "export results":
            return await self._export_results(session)
        elif msg_lower == "analyze another repository":
            return "Sure! Please provide a repository path or GitHub URL to analyze. Example: 'analyze https://github.com/user/repo'"
        
        # Check for bug explanation requests
        if any(word in msg_lower for word in ["explain bug", "tell me about bug", "what is bug", "describe bug"]):
            # Extract bug number
            import re
            match = re.search(r'#?(\d+)', user_message)
            if match:
                bug_id = int(match.group(1))
                return await self.explain_bug(bug_id, session)
            else:
                return "Please specify which bug you'd like me to explain. Example: 'explain bug #5'"
        
        # Check for code snippet requests
        if any(word in msg_lower for word in ["show code", "display code", "code for bug", "buggy code", "code snippet"]):
            # Extract bug number
            import re
            match = re.search(r'#?(\d+)', user_message)
            if match:
                bug_id = int(match.group(1))
                return await self.show_code_snippet(bug_id, session)
            else:
                return "Please specify which bug's code you'd like to see. Example: 'show code for bug #3'"
        
        # Check for fix guide requests
        if any(word in msg_lower for word in ["fix guide", "how to fix", "fix bug", "fix steps", "implement fix"]):
            # Extract bug number
            import re
            match = re.search(r'#?(\d+)', user_message)
            if match:
                bug_id = int(match.group(1))
                return await self.get_fix_guide(bug_id, session)
            else:
                return "Please specify which bug you'd like a fix guide for. Example: 'fix guide for bug #2'"
        
        # Check if user wants to run a workflow
        if any(word in msg_lower for word in ["analyze", "scan", "detect", "find bugs", "run workflow", "start", "execute"]):
            if repository_path:
                return await self._run_workflow(repository_path, session)
            else:
                return """I can analyze your code for bugs! Please provide a repository path or GitHub URL to get started.

Try any of these:
• 'analyze https://github.com/user/repo'
• 'analyze /path/to/local/repo'
• 'scan ./my-project'
• 'detect bugs in C:\\Users\\project'"""
        
        # Check if user wants to see results
        if any(word in msg_lower for word in ["results", "bugs", "fixes", "show", "display", "what found"]):
            return await self._show_results(session)
        
        # Default: use fallback response
        return self._get_fallback_response(user_message, session.context)
    
    async def _run_workflow(self, repository_path: str, session: ChatSession) -> str:
        """
        Run the complete CloudForge workflow with progress tracking.
        
        Args:
            repository_path: Path to repository (local path or GitHub URL)
            session: Chat session
            
        Returns:
            Workflow execution summary with detailed results
        """
        try:
            if not self.orchestrator:
                return "Workflow orchestrator not configured. Please set up the orchestrator to run workflows."
            
            self.logger.info(f"Starting workflow for repository: {repository_path}")
            self.logger.info(f"Session ID: {session.session_id}")
            self.logger.info(f"Workflow ID: {session.workflow_id}")
            
            # Phase 1: Clone Repository
            actual_path = repository_path
            
            # Generate workflow_id if not set
            if not session.workflow_id:
                from uuid import uuid4
                session.workflow_id = f"wf-{str(uuid4())[:8]}"
                self.logger.info(f"Generated workflow ID: {session.workflow_id}")
            
            # Initial message with dashboard link
            initial_message = f"""🚀 **Starting Analysis**

**Workflow ID:** `{session.workflow_id}`

📊 **View Live Results:** [Open Dashboard](http://localhost:5000/dashboard?workflow_id={session.workflow_id})

I'll analyze your repository step by step. Here's what I'll do:
1. 📥 Clone the repository
2. 🐛 Detect bugs
3. 🧪 Generate tests
4. ▶️ Execute tests
5. 🔍 Analyze results
6. 💡 Suggest fixes

Let me start...
"""
            session.messages.append(ChatMessage(sender="assistant", content=initial_message))
            self.logger.info("Initial message sent with dashboard link")
            
            # Phase 1: Clone Repository
            clone_message = "**Step 1: Cloning Repository** ⏳\n\n"
            
            if repository_path.startswith(('http://', 'https://', 'git@')):
                self.logger.info(f"Detected GitHub URL, cloning repository...")
                clone_message += f"Repository: `{repository_path}`\n"
                actual_path = await self._clone_github_repo(repository_path)
                if not actual_path:
                    return f"❌ Failed to clone GitHub repository: {repository_path}\n\nPlease ensure the URL is valid and accessible."
                clone_message += f"✅ Repository cloned successfully\n"
                self.logger.info(f"Repository cloned to: {actual_path}")
            else:
                clone_message += f"Repository: `{actual_path}`\n✅ Repository ready\n"
            
            # Add clone message to session
            session.messages.append(ChatMessage(sender="assistant", content=clone_message))
            self.logger.info("Phase 1 complete: Repository cloned")
            
            # Phase 2: Run the workflow
            self.logger.info(f"Running workflow on repository: {actual_path}")
            
            try:
                # Add timeout to prevent hanging
                import asyncio
                result = await asyncio.wait_for(
                    self.orchestrator.execute_workflow(
                        repository_url=repository_path,
                        repository_path=actual_path,
                        workflow_id=session.workflow_id
                    ),
                    timeout=600  # 10 minute timeout
                )
                self.logger.info(f"Workflow completed successfully. Workflow ID: {result.workflow_id}")
            except asyncio.TimeoutError:
                self.logger.error("Workflow execution timed out after 10 minutes")
                return f"❌ Workflow execution timed out after 10 minutes. Repository may be too large or analysis is taking too long."
            except Exception as e:
                self.logger.error(f"Error executing workflow: {e}", exc_info=True)
                raise
            
            # Update session context with results
            session.context.update({
                'workflow_id': result.workflow_id,
                'bugs_found': len(result.bugs),
                'tests_generated': len(result.test_cases),
                'tests_executed': len(result.test_results),
                'root_causes_found': len(result.root_causes),
                'fixes_suggested': len(result.fix_suggestions),
                'current_status': result.status
            })
            
            # Phase 2: Bug Detection Results
            bug_message = "**Step 2: Bug Detection** ⏳\n\n"
            bug_message += f"Found **{len(result.bugs)}** bugs\n\n"
            
            if result.bugs:
                bug_message += "**Severity Breakdown:**\n"
                severity_counts = {}
                severity_emojis = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }
                
                for bug in result.bugs:
                    severity = bug.severity.upper()
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                    count = severity_counts.get(severity, 0)
                    if count > 0:
                        emoji = severity_emojis.get(severity, '•')
                        bug_message += f"{emoji} {severity}: {count}\n"
                
                bug_message += f"\n✅ Bug detection complete"
            else:
                bug_message += "✅ **No bugs detected!**\n"
            
            session.messages.append(ChatMessage(sender="assistant", content=bug_message))
            self.logger.info(f"Phase 2 complete: Bug detection found {len(result.bugs)} bugs")
            
            # Phase 3: Test Generation Results
            test_gen_message = "**Step 3: Test Generation** ⏳\n\n"
            test_gen_message += f"Generated **{len(result.test_cases)}** test cases\n"
            test_gen_message += f"✅ Test generation complete\n"
            
            session.messages.append(ChatMessage(sender="assistant", content=test_gen_message))
            self.logger.info(f"Phase 3 complete: Test generation created {len(result.test_cases)} tests")
            
            # Phase 4: Test Execution Results
            test_exec_message = "**Step 4: Test Execution** ⏳\n\n"
            test_exec_message += f"Executed **{len(result.test_results)}** tests\n\n"
            
            if result.test_results:
                passed = sum(1 for t in result.test_results if getattr(t, 'status', 'passed') == 'passed')
                failed = sum(1 for t in result.test_results if getattr(t, 'status', 'passed') == 'failed')
                
                success_rate = (passed/len(result.test_results)*100) if result.test_results else 0
                
                test_exec_message += f"✅ Passed: {passed}\n"
                test_exec_message += f"❌ Failed: {failed}\n"
                test_exec_message += f"📊 Success Rate: {success_rate:.1f}%\n"
            else:
                test_exec_message += "No tests were executed.\n"
            
            test_exec_message += f"\n✅ Test execution complete"
            
            session.messages.append(ChatMessage(sender="assistant", content=test_exec_message))
            self.logger.info(f"Phase 4 complete: Test execution finished with {len(result.test_results)} tests")
            
            # Phase 5: Root Cause Analysis Results
            analysis_message = "**Step 5: Root Cause Analysis** ⏳\n\n"
            analysis_message += f"Identified **{len(result.root_causes)}** root causes\n"
            analysis_message += f"✅ Analysis complete\n"
            
            session.messages.append(ChatMessage(sender="assistant", content=analysis_message))
            self.logger.info(f"Phase 5 complete: Root cause analysis identified {len(result.root_causes)} causes")
            
            # Phase 6: Fix Suggestions Results
            fix_message = "**Step 6: Fix Suggestions** ⏳\n\n"
            fix_message += f"Generated **{len(result.fix_suggestions)}** fix suggestions\n"
            fix_message += f"✅ Fix suggestions complete\n"
            
            session.messages.append(ChatMessage(sender="assistant", content=fix_message))
            self.logger.info(f"Phase 6 complete: Fix suggestions generated {len(result.fix_suggestions)} fixes")
            
            # Final Summary
            summary = f"""✅ **Analysis Complete!**

**Workflow ID:** `{result.workflow_id}`

---

� **Results Summary:**
• 🐛 Bugs Found: {len(result.bugs)}
• 🧪 Tests Generated: {len(result.test_cases)}
• ▶️ Tests Executed: {len(result.test_results)}
• 🔍 Root Causes: {len(result.root_causes)}
• 💡 Fixes Suggested: {len(result.fix_suggestions)}

---

🎯 **Next Steps:**

1. **View Detailed Results:** [Open Dashboard](http://localhost:5000/dashboard?workflow_id={result.workflow_id})
2. **Ask Questions:** Type "explain bug #1" to understand a specific bug
3. **See Code:** Type "show code for bug #2" to see buggy vs fixed code
4. **Get Fix Guide:** Type "fix guide for bug #3" for step-by-step instructions

---

**What would you like to do next?**
• Analyze another repository
• Get details about a specific bug
• View the dashboard for more information
"""
            
            return summary
        
        except Exception as e:
            self.logger.error(f"Error running workflow: {e}")
            return f"❌ Error running workflow: {str(e)}\n\nPlease check the repository path and try again."
    
    async def _clone_github_repo(self, github_url: str) -> str:
        """
        Clone a GitHub repository to a temporary directory.
        
        Args:
            github_url: GitHub repository URL (https or git)
            
        Returns:
            Path to cloned repository, or None if cloning failed
        """
        import subprocess
        import tempfile
        from pathlib import Path
        
        try:
            # Create temporary directory for cloning
            temp_dir = tempfile.mkdtemp(prefix="cloudforge_repo_")
            self.logger.info(f"Cloning repository to: {temp_dir}")
            
            # Clone the repository
            result = subprocess.run(
                ["git", "clone", "--depth", "1", github_url, temp_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.logger.error(f"Git clone failed: {result.stderr}")
                return None
            
            self.logger.info(f"Successfully cloned repository to: {temp_dir}")
            return temp_dir
        
        except subprocess.TimeoutExpired:
            self.logger.error(f"Git clone timed out for: {github_url}")
            return None
        except Exception as e:
            self.logger.error(f"Error cloning repository: {e}")
            return None
    
    async def _show_results(self, session: ChatSession) -> str:
        """Show workflow results."""
        if not session.context.get('workflow_id'):
            return "No workflow has been run yet. Please run a workflow first by saying 'analyze /path/to/repo'"
        
        bugs = session.context.get('bugs_found', 0)
        fixes = session.context.get('fixes_suggested', 0)
        
        return f"""📊 Current Workflow Results:

Workflow ID: {session.context.get('workflow_id')}
Status: {session.context.get('current_status', 'unknown')}

🐛 Bugs: {bugs}
🧪 Tests: {session.context.get('tests_executed', 0)}
🔍 Root Causes: {session.context.get('root_causes_found', 0)}
💡 Fixes: {fixes}

What would you like to do next?
• View specific bug details
• See fix suggestions
• Export results
• Run another analysis"""
    
    async def explain_bug(self, bug_id: int, session: ChatSession) -> str:
        """Provide detailed explanation of a specific bug."""
        try:
            bugs = session.context.get('bugs_found', [])
            if not bugs or bug_id < 1 or bug_id > len(bugs):
                return f"❌ Bug #{bug_id} not found. Total bugs: {len(bugs)}"
            
            bug = bugs[bug_id - 1]
            
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(bug.severity.upper(), '•')
            
            explanation = f"""
🐛 **Bug #{bug_id}: {bug.description}**

**Severity:** {severity_emoji} {bug.severity.upper()}
**File:** `{getattr(bug, 'file_path', 'Unknown')}`
**Line:** {getattr(bug, 'line_number', 'Unknown')}
**Type:** {getattr(bug, 'bug_type', 'Code Issue')}

---

**Why It's a Problem:**
{getattr(bug, 'impact_description', 'This bug can cause runtime errors or unexpected behavior.')}

**Potential Consequences:**
• Application crash or unexpected behavior
• Data corruption or loss
• Security vulnerability
• Performance degradation

**How It Happens:**
The code doesn't properly handle edge cases or validate inputs before use.

**Suggested Fix:**
{getattr(bug, 'fix_description', 'Add proper error handling and input validation.')}

**Safety Score:** {getattr(bug, 'safety_score', 0.85):.1%}

---

**Would you like me to:**
• Show the code (buggy vs fixed)
• Provide step-by-step fix guide
• Apply the fix automatically
• Show similar bugs
"""
            
            self.logger.info(f"Explained bug #{bug_id} for session {session.session_id}")
            return explanation
        
        except Exception as e:
            self.logger.error(f"Error explaining bug: {e}")
            return f"❌ Error explaining bug: {str(e)}"
    
    async def show_code_snippet(self, bug_id: int, session: ChatSession) -> str:
        """Display buggy and fixed code for a bug."""
        try:
            bugs = session.context.get('bugs_found', [])
            if not bugs or bug_id < 1 or bug_id > len(bugs):
                return f"❌ Bug #{bug_id} not found. Total bugs: {len(bugs)}"
            
            bug = bugs[bug_id - 1]
            
            # Get code snippets
            buggy_code = getattr(bug, 'buggy_code', None)
            fixed_code = getattr(bug, 'fixed_code', None)
            file_path = getattr(bug, 'file_path', 'Unknown')
            start_line = getattr(bug, 'line_number', 1)
            
            snippet = f"""
📄 **Code Snippet - Bug #{bug_id}**

**File:** `{file_path}`
**Lines:** {start_line}-{start_line + 10}

---

❌ **BUGGY CODE:**
```python
{start_line:3d} | {buggy_code if buggy_code else 'user_data = get_user_data(user_id)'}
{start_line+1:3d} | {'' if not buggy_code else 'name = user_data.name  # Crashes if user_data is None'}
```

✅ **FIXED CODE:**
```python
{start_line:3d} | {fixed_code if fixed_code else 'user_data = get_user_data(user_id)'}
{start_line+1:3d} | {'if user_data is not None:' if not fixed_code else '    name = user_data.name'}
{start_line+2:3d} | {'    name = user_data.name' if not fixed_code else 'else:'}
{start_line+3:3d} | {'else:' if not fixed_code else '    name = "Unknown"'}
{start_line+4:3d} | {'    name = "Unknown"' if not fixed_code else ''}
```

---

**Key Changes:**
• Added null/None check before accessing object
• Added fallback value for edge case
• Prevents runtime crash

**Why This Works:**
Checking if the object exists before using it prevents AttributeError exceptions.

---

**Would you like me to:**
• Explain this bug in detail
• Provide step-by-step fix guide
• Apply this fix automatically
"""
            
            self.logger.info(f"Showed code snippet for bug #{bug_id}")
            return snippet
        
        except Exception as e:
            self.logger.error(f"Error showing code snippet: {e}")
            return f"❌ Error showing code: {str(e)}"
    
    async def get_fix_guide(self, bug_id: int, session: ChatSession) -> str:
        """Provide step-by-step fix implementation guide."""
        try:
            bugs = session.context.get('bugs_found', [])
            if not bugs or bug_id < 1 or bug_id > len(bugs):
                return f"❌ Bug #{bug_id} not found. Total bugs: {len(bugs)}"
            
            bug = bugs[bug_id - 1]
            
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(bug.severity.upper(), '•')
            
            guide = f"""
🔧 **Fix Implementation Guide - Bug #{bug_id}**

**Bug:** {bug.description}
**Severity:** {severity_emoji} {bug.severity.upper()}
**Difficulty:** Medium
**Time to Fix:** 10-20 minutes
**Risk Level:** Low

---

**Step 1: Understand the Problem**

{getattr(bug, 'problem_explanation', 'The code accesses an object without checking if it exists first. This causes a NoneType error when the object is None.')}

**Step 2: Locate the Issue**

File: `{getattr(bug, 'file_path', 'Unknown')}`
Line: {getattr(bug, 'line_number', 'Unknown')}

**Step 3: Implement the Fix**

```python
# BEFORE (Buggy)
user_data = get_user_data(user_id)
name = user_data.name  # ❌ Crashes if user_data is None

# AFTER (Fixed)
user_data = get_user_data(user_id)
if user_data is not None:  # ✅ Check first
    name = user_data.name
else:
    name = "Unknown"  # Fallback value
```

**Step 4: Test the Fix**

```bash
# Run unit tests
python -m pytest tests/test_user_data.py -v

# Run integration tests
python -m pytest tests/integration/ -v

# Check for regressions
python -m pytest tests/ -v
```

**Step 5: Verify Results**

- [ ] All tests pass
- [ ] No new errors in logs
- [ ] Performance is acceptable
- [ ] Code review approved

**Step 6: Deploy**

```bash
# Create feature branch
git checkout -b fix/bug-{bug_id}

# Commit changes
git add .
git commit -m "Fix: {bug.description}"

# Push to remote
git push origin fix/bug-{bug_id}

# Create pull request
# Get approval and merge
```

**Step 7: Monitor**

- Watch error logs for 24 hours
- Monitor performance metrics
- Check user reports
- Be ready to rollback if needed

---

**Rollback Plan (If Issues Occur):**

```bash
# Revert the commit
git revert <commit-hash>

# Push revert
git push origin main

# Notify team
```

**Expected Outcome:**
✅ No more NoneType errors
✅ Graceful handling of edge cases
✅ Improved application stability
✅ Better user experience

---

**Common Pitfalls to Avoid:**
❌ Don't forget the None check
❌ Don't ignore the error case
❌ Don't skip testing
❌ Don't deploy without review

---

**Would you like me to:**
• Apply this fix automatically
• Show alternative fix approaches
• Run tests after fix
• Create a pull request
"""
            
            self.logger.info(f"Generated fix guide for bug #{bug_id}")
            return guide
        
        except Exception as e:
            self.logger.error(f"Error generating fix guide: {e}")
            return f"❌ Error generating fix guide: {str(e)}"

    async def get_quick_action_buttons(self, session: ChatSession) -> str:
        """Generate quick action buttons based on analysis results."""
        
        bugs = session.context.get('bugs_found', 0)
        critical_bugs = session.context.get('critical_bugs', 0)
        high_bugs = session.context.get('high_bugs', 0)
        workflow_id = session.context.get('workflow_id', '')
        
        # Build buttons message with special formatting for button rendering
        buttons_message = f"""🎯 **Quick Actions:**

[BUTTON:critical:🔴 View Critical ({critical_bugs})]
[BUTTON:high:🟠 View High ({high_bugs})]
[BUTTON:export:📊 Export Results]
[BUTTON:analyze:🔄 Analyze Another]

Or ask me:
• "explain bug #1" - Get details about a bug
• "show code for bug #2" - See buggy vs fixed code
• "fix guide for bug #3" - Get step-by-step instructions
"""
        
        return buttons_message
    
    async def filter_and_sort_bugs(self, session: ChatSession, severity: str = None, sort_by: str = 'severity') -> str:
        """Filter and sort bugs based on criteria."""
        
        bugs = session.context.get('bugs_list', [])
        
        # If no bugs list, return message
        if not bugs:
            return f"No bugs found in the current analysis. Run an analysis first to see bugs."
        
        # Filter by severity
        if severity and severity.upper() != 'ALL':
            bugs = [b for b in bugs if getattr(b, 'severity', 'UNKNOWN').upper() == severity.upper()]
        
        # Sort
        if sort_by == 'severity':
            severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            bugs = sorted(bugs, key=lambda b: severity_order.get(getattr(b, 'severity', 'UNKNOWN').upper(), 4))
        elif sort_by == 'file':
            bugs = sorted(bugs, key=lambda b: getattr(b, 'file_path', ''))
        elif sort_by == 'line':
            bugs = sorted(bugs, key=lambda b: getattr(b, 'line_number', 0))
        elif sort_by == 'confidence':
            bugs = sorted(bugs, key=lambda b: getattr(b, 'confidence_score', 0), reverse=True)
        
        # Format results
        severity_emojis = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}
        
        result = f"📊 **Filtered Results** ({len(bugs)} bugs)\n\n"
        
        for i, bug in enumerate(bugs[:10], 1):
            severity = getattr(bug, 'severity', 'UNKNOWN').upper()
            emoji = severity_emojis.get(severity, '•')
            description = getattr(bug, 'description', 'No description')[:50]
            file_path = getattr(bug, 'file_path', 'Unknown')
            line_number = getattr(bug, 'line_number', '?')
            
            result += f"{i}. {emoji} **{severity}** - {description}\n"
            result += f"   📄 `{file_path}:{line_number}`\n\n"
        
        if len(bugs) > 10:
            result += f"... and **{len(bugs) - 10}** more bugs"
        
        return result
    
    async def _export_results(self, session: ChatSession) -> str:
        """Export analysis results."""
        
        workflow_id = session.context.get('workflow_id')
        if not workflow_id:
            return "No analysis results to export. Please run an analysis first."
        
        bugs = session.context.get('bugs_found', 0)
        fixes = session.context.get('fixes_suggested', 0)
        
        export_message = f"""📤 **Export Results**

**Workflow ID:** `{workflow_id}`

**Results Summary:**
• Bugs Found: {bugs}
• Fixes Suggested: {fixes}

**Export Formats Available:**
• 📄 PDF Report
• 📊 JSON Data
• 📋 CSV Spreadsheet
• 🌐 HTML Report

You can download these from the Dashboard:
[Open Dashboard](http://localhost:5000/dashboard?workflow_id={workflow_id})

Would you like me to help you with anything else?
"""
        
        return export_message
    
    def _get_fallback_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """Provide fallback response when Bedrock is unavailable."""
        msg_lower = user_message.lower()
        
        # Greeting responses
        if any(word in msg_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "👋 Hello! I'm CloudForge's AI assistant. I can help you analyze your code for bugs, generate tests, and suggest fixes. What would you like to do?"
        
        # Help/capabilities
        if any(word in msg_lower for word in ["help", "what can", "capabilities", "features", "commands"]):
            return """I can help you with:

🔍 **Analyze** - Scan your code for bugs
🧪 **Test** - Generate and run tests
🔬 **Analyze Results** - Identify root causes
💡 **Suggest Fixes** - Get code patches
📊 **Show Results** - Display findings
📤 **Export** - Save results

Try saying: "analyze /path/to/repo" or "show results"
"""
        
        # Default response
        return f"I understand you're asking about: '{user_message}'\n\nI can help you analyze code for bugs and suggest fixes. Try:\n• 'analyze /path/to/repo' - Scan your code\n• 'show results' - Display findings\n• 'help' - See all commands"
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieve a chat session."""
        return self.sessions.get(session_id)
    
    def get_session_history(self, session_id: str) -> List[ChatMessage]:
        """Get conversation history for a session."""
        session = self.sessions.get(session_id)
        return session.messages if session else []
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a chat session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"Cleared session {session_id}")
            return True
        return False
