output "api_url" {
  value = "http://${aws_instance.api.public_ip}"
}

output "docs_url" {
  value = "http://${aws_instance.api.public_ip}/docs"
}
