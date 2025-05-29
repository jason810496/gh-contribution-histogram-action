from typing import List, Tuple

def parse_targets(targets: str) -> List[Tuple[str, str, str]]:
    """
    Parse a string of targets into a list of (username, repo_owner, repo_name) tuples.
    
    Args:
        targets (str): String containing targets in the format 'username@owner/repo'.
                      Multiple targets can be separated by spaces or commas.
    
    Returns:
        List[Tuple[str, str, str]]: List of tuples containing (username, repo_owner, repo_name)
    
    Raises:
        ValueError: If the input format is invalid
    """
    if not targets or not targets.strip():
        raise ValueError("Empty targets string")
        
    # Split by both space and comma, then filter out empty strings
    target_arr = [t.strip() for t in targets.replace(',', ' ').split() if t.strip()]
    parsed_targets = []
    
    for target in target_arr:
        if target.count('@') != 1:
            raise ValueError(f"Invalid repository format: {target}")
        try:
            username, repo = target.split("@")
            if not username or not repo:
                raise ValueError(f"Invalid target format: {target}")
                
            try:
                repo_owner, repo_name = repo.split("/")
                if not repo_owner or not repo_name:
                    raise ValueError(f"Invalid repository format: {repo}")
            except ValueError as e:
                if "not enough values to unpack" in str(e) or "too many values to unpack" in str(e):
                    raise ValueError(f"Invalid repository format: {repo}")
                raise
                
            parsed_targets.append((username, repo_owner, repo_name))
        except ValueError as e:
            if "Invalid repository format" in str(e):
                raise
            raise ValueError(f"Error parsing target '{target}': {str(e)}. Expected format: username@owner/repo")
            
    return parsed_targets
