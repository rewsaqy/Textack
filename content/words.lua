-- Word pools (mirrors textack/core/words.py).
return {
  tier1 = { "ls", "cd", "pwd", "cat", "echo", "clear", "whoami", "mkdir",
            "touch", "rm" },
  tier2 = { "sudo", "grep", "chmod", "chown", "ps aux", "kill", "tar -xzf",
            "ssh", "curl", "wget" },
  tier3 = { "sudo apt update", "ps aux | grep nginx", "chmod +x main.py",
            "systemctl status sshd", "find /etc -name nginx",
            "tail -f /var/log/syslog", "df -h | grep sda",
            "ls -la ~/Documents" },
}
