# AWS infrastructure (separate from Oracle)

This folder defines a small, single-instance AWS environment for the existing
Docker Compose deployment. It does not deploy application code, copy Oracle
data, configure DNS, or change Oracle. Nothing is created until Terraform is
run against an AWS account.

## Resources in this first learning step

- A dedicated VPC, one public subnet, an Internet Gateway, and a route table.
- A security group allowing HTTP/HTTPS publicly and SSH only from one IPv4 CIDR.
- One Ubuntu 24.04 ARM64 EC2 instance with encrypted 20 GiB gp3 root storage.
- A separate encrypted gp3 EBS data volume for SQLite, protected from accidental
  Terraform destruction and mounted at `/srv/viaje-claro-data`.
- The local SSH public key registered with AWS. The private key stays local.
- First-boot installation of Docker Engine, the Compose plugin, and Caddy from
  their official APT repositories. Caddy initially proxies HTTP to
  `127.0.0.1:5173`, matching the current Compose port mapping.

There is no NAT Gateway, load balancer, managed database, or fixed public IP.
The instance's public IP can change after replacement or a stop/start cycle.
An EC2 instance, EBS storage, and public IPv4 may incur charges. Check current
pricing for the chosen region and instance type before creating resources.

## Relationship to the existing project

The existing `compose.yaml` and Dockerfiles can be reused. Caddy runs on the
Ubuntu host and proxies to the web container at `127.0.0.1:5173`; the Compose
file already keeps its web and API ports on loopback. On AWS, use
`compose.aws.yaml` to bind `/data` to the separately mounted EBS data volume.
Do not use the Oracle Docker volume name on AWS or assume a fresh volume already
contains SQLite data. The bootstrap formats the EBS volume only when it has no
filesystem; it refuses to format a non-ext4 volume. It does not clone the repo,
write environment secrets, start Compose, or copy application data. After a DNS
name is selected, change the Caddy site address from `:80` to that hostname to
enable automatic HTTPS.

The bootstrap script runs only on the first boot of a newly created instance.
Its output is written to `/var/log/travel-expenses-bootstrap.log` (and the
cloud-init output log). Updating the script later does not automatically rerun
its commands on an existing instance.

`prevent_destroy` on the EBS data volume makes `terraform destroy` stop until
that protection is deliberately removed. The volume still has ongoing storage
charges while it exists, even if detached. Take a separate verified backup
before any restore or infrastructure change.

Before a production move, take and verify an Oracle SQLite backup, restore it
to a separate AWS volume, and validate the app using a temporary hostname or
IP. Keep Oracle and its DNS configuration untouched until the AWS copy has
been checked. Supabase authentication redirect URLs will need the eventual
AWS hostname when a cutover is explicitly chosen.

## Restore the verified SQLite backup on AWS (manual step)

After the AWS host has been created and bootstrapped, copy the verified backup
to the host without putting it in Git. Stop the application before restoring.
Keep the original file unchanged, and copy it to the mounted data volume as
`expenses.db`; then set ownership/permissions and verify the database before
starting Compose. The AWS Compose command must include both files:

```bash
sudo docker compose --env-file backend/.env.docker \
  -f compose.yaml -f compose.aws.yaml config --quiet
sudo docker compose --env-file backend/.env.docker \
  -f compose.yaml -f compose.aws.yaml up -d --build
```

Prepare the exact restore commands for the selected backup and volume before
running them. Do not restore over an active database, and do not change Oracle's
DNS or delete its data during validation.

## Prepare locally

1. Create an SSH key pair locally if needed; provide Terraform only the `.pub`
   path. Never place the private key in this folder or in Git.
2. Copy `terraform.tfvars.example` to `terraform.tfvars` and set the region,
   your real public IPv4 CIDR with `/32`, and the public key path.
3. Initialize and review Terraform locally. Inspect the full plan and expected
   AWS charges before any apply. Do not apply without explicit approval.

Terraform state can contain infrastructure details. Keep local state and
`.terraform/` out of version control; do not add cloud credentials to files.
