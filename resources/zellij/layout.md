# Zellij

Zellij allows you to open multiple windows and tabs within a terminal. A zellij configuration can be save to a file called a zellij layout.

## Zellij Layouts

The layout used in this demo : [ai_gpu_dashboard.kdl](ai_gpu_dashboard.kdl)

![Zellij Layout](/assets/images/zellij.png)

To use this layout save `ai_gpu_dashboard.kdl` to `~/.config/zellij/layouts/` and from `gpu-cost-optimisation` project home run  

```bash
zellij delete-session --force AI-GPU-Demo && \
zellij --session AI-GPU-Demo --layout ai_gpu_dashboard
```