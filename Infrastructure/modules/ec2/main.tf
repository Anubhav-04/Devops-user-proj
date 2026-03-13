provider "aws" {
  region = var.region
}

resource "aws_instance" "users" {
  ami = var.ami-id
  key_name = var.secret-key
  tags = {
    Name = var.instace_name
  }
}