import os
from datetime import datetime
import openai
import github
from github import Github
import time
import json
from git import Repo

class AutoCodeGenerator:
    def __init__(self):
        """Initialize with necessary API tokens and repository information."""
        self.github_token = os.getenv('GITHUB_TOKEN')  # Get GitHub token from environment variables
        self.openai_key = os.getenv('OPENAI_API_KEY')  # Get OpenAI API key from environment variables
        self.repo_name = os.getenv('REPO_NAME')  # Get the repository name from environment variables

        # Initialize the GitHub API client
        self.g = Github(self.github_token)
        self.repo = self.g.get_repo(self.repo_name)  # Access the repository using the GitHub API
        openai.api_key = self.openai_key  # Set OpenAI API key for usage in code generation

    def analyze_coding_style(self, num_commits=50):
        """Analyze recent commits to understand coding patterns."""
        commits = list(self.repo.get_commits()[:num_commits])  # Get recent commits (limit to 50 by default)
        
        coding_patterns = {
            'indentation': [],
            'naming_conventions': [],
            'comment_style': [],
            'function_lengths': [],
            'common_patterns': {}
        }

        for commit in commits:  # Iterate through each commit
            files = commit.files  # Get files changed in the commit
            for file in files:
                if file.filename.endswith('.py'):  # Only analyze Python files
                    content = file.patch if hasattr(file, 'patch') else ''  # Get the content of the file change
                    if content:
                        # Analyze indentation by counting leading spaces in each line
                        lines = content.split('\n')
                        for line in lines:
                            if line.strip():  # Ignore empty lines
                                spaces = len(line) - len(line.lstrip())  # Calculate leading spaces
                                coding_patterns['indentation'].append(spaces)
                        
                        # Analyze naming conventions using regex (for variables and functions)
                        import re
                        variable_names = re.findall(r'\b(?:var|let|const)\s+(\w+)', content)
                        function_names = re.findall(r'\bdef\s+(\w+)', content)
                        coding_patterns['naming_conventions'].extend(variable_names + function_names)

        return coding_patterns  # Return the analysis results

    def generate_improvements(self, file_path):
        """Generate code improvements based on analyzed patterns."""
        if not os.path.exists(file_path):  # Check if the file exists locally (e.g., if running locally)
            print(f"File not found: {file_path}. Skipping.")
            return None  # Skip the file if not found

        with open(file_path, 'r') as file:
            current_code = file.read()  # Read the current code from the file

        # Prepare the prompt for OpenAI's GPT-4 model to generate improvements
        prompt = f"""
        Based on this code, suggest improvements while maintaining the same style:
        
        {current_code}
        
        Provide only the improved code without explanations.
        """

        # Call OpenAI API to get improved code suggestions
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content  # Return the generated improvements

    def create_pull_request(self, file_path, improvements):
        """Create a pull request with suggested improvements."""
        # Create a new branch based on current time to ensure uniqueness
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        branch_name = f'auto_improvement_{current_time}'
        
        # Get the default branch of the repository
        default_branch = self.repo.default_branch
        
        # Create a new branch using the default branch as a reference
        ref = self.repo.get_git_ref(f'heads/{default_branch}')
        self.repo.create_git_ref(f'refs/heads/{branch_name}', ref.object.sha)
        
        # Update the file with the improvements in the new branch
        current_file = self.repo.get_contents(file_path, ref=default_branch)
        self.repo.update_file(
            file_path,
            f'Auto-improvement for {file_path}',
            improvements,
            current_file.sha,
            branch=branch_name
        )
        
        # Create a pull request with the improvements
        pr = self.repo.create_pull(
            title=f'Auto-generated improvements for {file_path}',
            body='These improvements were automatically generated based on the repository\'s coding patterns.',
            head=branch_name,
            base=default_branch
        )
        
        return pr.number  # Return the pull request number

    def run_night_cycle(self):
        """Run the complete night cycle of improvements."""
        try:
            # 1. Analyze coding patterns
            patterns = self.analyze_coding_style()
            
            # 2. Find Python files in the repository
            contents = self.repo.get_contents("")  # Get the root contents of the repo
            python_files = []  # List to store Python file paths
            
            # Iterate through the repository contents
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":  # If it's a directory, look inside it
                    contents.extend(self.repo.get_contents(file_content.path))
                elif file_content.name.endswith(".py"):  # If it's a Python file, add it to the list
                    python_files.append(file_content.path)
            
            # 3. Generate improvements for each Python file
            for file_path in python_files:
                improvements = self.generate_improvements(file_path)  # Generate improvements for the file
                if improvements:
                    pr_number = self.create_pull_request(file_path, improvements)  # Create a PR with the improvements
                    print(f"Created PR #{pr_number} for {file_path}")
                
                # Sleep to avoid hitting GitHub API rate limits
                time.sleep(5)
                
        except Exception as e:
            print(f"Error during night cycle: {str(e)}")

# Main execution
if __name__ == "__main__":
    # Get configuration from environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    repo_name = os.getenv('REPO_NAME')
    
    # Check if any of the required environment variables are missing
    if not github_token or not openai_key or not repo_name:
        raise ValueError("Missing required environment variables")

    # Initialize the AutoCodeGenerator with the environment variables
    generator = AutoCodeGenerator()
    
    # Run the night cycle to perform code improvements
    generator.run_night_cycle()
