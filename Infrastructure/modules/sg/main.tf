resource "aws_security_group" "web-sg" {
  name = "web-sg"
  ingress {
    from_port = 3000
    to_port = 3000
    cidr_blocks = "0.0.0.0/0"
  }
  egress {
    from_port = 0
    to_port = 0
    cidr_blocks = "0.0.0.0/0"
  }
}