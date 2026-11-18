variable "region" {
  type    = string
  default = "ap-south-1" # Mumbai
}

variable "name" {
  type    = string
  default = "kitchenflow"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "repo_url" {
  type        = string
  description = "HTTPS URL of the GitHub repo to deploy, e.g. https://github.com/<you>/kitchenflow.git"
}

variable "allowed_cidr" {
  type        = string
  default     = "0.0.0.0/0"
  description = "Who may reach the API. Narrow this (e.g. your IP/32) for anything beyond a demo."
}

variable "api_key" {
  type      = string
  sensitive = true
  default   = ""
}
