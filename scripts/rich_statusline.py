#!/usr/bin/env python3
"""
Rich-enhanced statusline for Claude Code
Provides enhanced visual formatting using the Rich library
"""

import argparse
import json
import sys

def create_rich_statusline(data):
    """Create a rich-formatted statusline using Rich library components"""
    
    # Import Rich components
    try:
        from rich.console import Console  # type: ignore
        from rich.text import Text  # type: ignore
    except ImportError:
        # Fallback to plain text if Rich not available
        return create_fallback_statusline(data)
    
    console = Console()
    
    # Parse input data
    model = data.get('model', 'Unknown')
    cost = data.get('cost', '$0.00 today')
    git_status = data.get('git', 'no-git')
    cwd = data.get('cwd', 'unknown')
    output_style = data.get('style', 'default')
    context_info = data.get('context', {})
    recent_prompts = data.get('prompts', '')
    
    # Create main status line with better spacing and colors
    main_line = Text()
    main_line.append("🤖 ", style="bold white")
    main_line.append(f"{model}", style="bold bright_cyan")
    main_line.append("  💰 ", style="bold white")
    main_line.append(f"{cost}", style="bold bright_green")
    main_line.append("  🎨 ", style="bold white")
    main_line.append(f"{output_style}", style="bold bright_blue")
    main_line.append("  📁 ", style="bold white")
    main_line.append(f"{cwd}", style="bold bright_magenta")
    
    # Create git status line with enhanced styling
    git_line = Text()
    git_line.append("🌿 ", style="bold white")
    git_line.append(f"{git_status}", style="bold bright_yellow")
    
    # Create context progress line if available
    context_line = None
    if context_info:
        used = context_info.get('used', 0)
        total = context_info.get('total', 200000)
        percentage = (used / total * 100) if total > 0 else 0
        
        # Create a more compact progress display
        context_line = Text()
        context_line.append("🧠 ", style="bold white")
        context_line.append("Context: ", style="bold white")
        
        # Color-coded progress bar
        bar_width = 20
        filled = int(percentage / 100 * bar_width)
        empty = bar_width - filled
        
        # Choose colors based on usage
        if percentage >= 90:
            bar_color = "bright_red"
        elif percentage >= 70:
            bar_color = "bright_yellow"
        else:
            bar_color = "bright_green"
        
        context_line.append("█" * filled, style=f"bold {bar_color}")
        context_line.append("░" * empty, style="dim white")
        context_line.append(f" {percentage:.1f}%", style=f"bold {bar_color}")
        
        # Format tokens
        if used >= 1000000:
            used_str = f"{used/1000000:.1f}M"
        elif used >= 1000:
            used_str = f"{used/1000:.0f}k"
        else:
            used_str = str(used)
            
        if total >= 1000000:
            total_str = f"{total/1000000:.1f}M"
        elif total >= 1000:
            total_str = f"{total/1000:.0f}k"
        else:
            total_str = str(total)
            
        context_line.append(f" ({used_str}/{total_str})", style="dim white")
    
    # Create recent prompts line if available  
    prompts_line = None
    if recent_prompts:
        prompts_line = Text()
        prompts_line.append("💬 ", style="bold white")
        prompts_line.append("Recent: ", style="bold white")
        prompts_line.append(f"{recent_prompts}", style="bold on purple white")
    
    # Display all lines with proper spacing
    console.print(main_line)
    console.print(git_line)
    
    if context_line:
        console.print(context_line)
    
    if prompts_line:
        console.print(prompts_line)

def create_fallback_statusline(data):
    """Fallback statusline without Rich (plain text)"""
    model = data.get('model', '🤖 Unknown')
    cost = data.get('cost', '$0.00 today')
    git_status = data.get('git', '🌿 no-git')
    cwd = data.get('cwd', '📁 unknown')
    output_style = data.get('style', 'default')
    recent_prompts = data.get('prompts', '')
    
    # Use sys.stdout.write for direct terminal output (not logging)
    sys.stdout.write(f"{model} | 💰 {cost} | 🎨 {output_style} | {git_status} | {cwd}\n")
    if recent_prompts:
        sys.stdout.write(f"💬 Recent: {recent_prompts}\n")
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description='Rich-enhanced statusline')
    parser.add_argument('--model', default='Unknown', help='Model name')
    parser.add_argument('--cost', default='$0.00 today', help='Daily cost')
    parser.add_argument('--git', default='🌿 no-git', help='Git status')
    parser.add_argument('--cwd', default='📁 unknown', help='Current directory')
    parser.add_argument('--style', default='default', help='Output style')
    parser.add_argument('--prompts', default='', help='Recent prompts')
    parser.add_argument('--context-used', type=int, default=0, help='Context tokens used')
    parser.add_argument('--context-total', type=int, default=200000, help='Context token limit')
    parser.add_argument('--context-percentage', type=float, default=0, help='Context usage percentage')
    parser.add_argument('--json', help='JSON input with all parameters')
    
    args = parser.parse_args()
    
    # Parse JSON input if provided
    if args.json:
        try:
            data = json.loads(args.json)
        except json.JSONDecodeError:
            sys.stderr.write("Error: Invalid JSON input\n")
            return 1
    else:
        # Use command line arguments
        data = {
            'model': args.model,
            'cost': args.cost,
            'git': args.git,
            'cwd': args.cwd,
            'style': args.style,
            'prompts': args.prompts,
            'context': {
                'used': args.context_used,
                'total': args.context_total,
                'percentage': args.context_percentage
            } if args.context_used > 0 else {}
        }
    
    create_rich_statusline(data)
    return 0

if __name__ == '__main__':
    sys.exit(main())