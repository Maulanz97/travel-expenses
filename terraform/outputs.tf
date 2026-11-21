output "instance_public_ip" {
  description = "Public IPv4 address; it can change if the instance is replaced or stopped."
  value       = aws_instance.app.public_ip
}

output "ssh_command" {
  description = "SSH command template; replace the private key path with your local key."
  value       = "ssh -i <private-key-path> ubuntu@${aws_instance.app.public_ip}"
}
