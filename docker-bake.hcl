
target "frappe" {
  context = "."
  dockerfile = "Dockerfile"
  tags = [ "frappe:dev" ]
}

