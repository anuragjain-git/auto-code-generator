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
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.repo_name = os.getenv('REPO_NAME')
        self.g = Github(self.github_token)
        self.repo = self.g.get_repo(self.repo_name)
        openai.api_key = self.openai_key

    def analyze_coding_style(self, num_commits=50):
        """Analyze recent commits to understand coding patterns."""
        commits = list(self.repo.get_commits()[:num_commits])
        coding_patterns = {
            'indentation': [],
            'naming_conventions': [],
            'comment_style': [],
            'function_lengths': [],
            'common_patterns': {}
        }
        
        for commit in commits:
            files = commit.files
            for file in files:
                if file.filename.endswith('.py'):  # Analyze Python files
                    content = file.patch if hasattr(file, 'patch') else ''
                    if content:
                        # Analyze indentation
                        lines = content.split('\n')
                        for line in lines:
                            if line.strip():
                                spaces = len(line) - len(line.lstrip())
                                coding_patterns['indentation'].append(spaces)
                        
                        # Analyze naming conventions
                        import re
                        variable_names = re.findall(r'\b(?:var|let|const)\s+(\w+)', content)
                        function_names = re.findall(r'\bdef\s+(\w+)', content)
                        coding_patterns['naming_conventions'].extend(variable_names + function_names)

        return coding_patterns

    def generate_improvements(self, file_path):
        """Generate code improvements based on analyzed patterns."""
        with open(file_path, 'r') as file:
            current_code = file.read()

        prompt = f"""
        Based on this code, suggest improvements while maintaining the same style:
        
        {current_code}
        
        Provide only the improved code without explanations.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    def create_pull_request(self, file_path, improvements):
        """Create a pull request with suggested improvements."""
        # Create a new branch
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        branch_name = f'auto_improvement_{current_time}'
        
        # Get the default branch
        default_branch = self.repo.default_branch
        
        # Create new branch
        ref = self.repo.get_git_ref(f'heads/{default_branch}')
        self.repo.create_git_ref(f'refs/heads/{branch_name}', ref.object.sha)
        
        # Update file in new branch
        current_file = self.repo.get_contents(file_path, ref=default_branch)
        self.repo.update_file(
            file_path,
            f'Auto-improvement for {file_path}',
            improvements,
            current_file.sha,
            branch=branch_name
        )
        
        # Create pull request
        pr = self.repo.create_pull(
            title=f'Auto-generated improvements for {file_path}',
            body='These improvements were automatically generated based on the repository\'s coding patterns.',
            head=branch_name,
            base=default_branch
        )
        
        return pr.number

    def run_night_cycle(self):
        """Run the complete night cycle of improvements."""
        try:
            # 1. Analyze patterns
            patterns = self.analyze_coding_style()
            
            # 2. Find Python files in repo
            contents = self.repo.get_contents("")
            python_files = []
            
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(self.repo.get_contents(file_content.path))
                elif file_content.name.endswith(".py"):
                    python_files.append(file_content.path)
            
            # 3. Generate improvements for each file
            for file_path in python_files:
                improvements = self.generate_improvements(file_path)
                if improvements:
                    pr_number = self.create_pull_request(file_path, improvements)
                    print(f"Created PR #{pr_number} for {file_path}")
                
                # Sleep to avoid API rate limits
                time.sleep(5)
                
        except Exception as e:
            print(f"Error during night cycle: {str(e)}")

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
    
    # Run the night cycle
    generator.run_night_cycle()
