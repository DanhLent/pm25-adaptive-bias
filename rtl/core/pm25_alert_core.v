// Sequential RTL implementation of pm25_core_v1_adaptive_bias_fixed.
module pm25_alert_core #(
    parameter integer ALPHA_SHIFT = 3
) (
    input clk,
    input rst_n,
    input sample_valid,
    input qc_ok,
    input [4:0] hour,
    input signed [31:0] cams_pm25_x16,
    input signed [31:0] pa_pm25_x16,
    output wire sample_ready,
    output reg result_valid,
    output reg accepted,
    output reg [4:0] hour_out,
    output reg signed [31:0] bias_before_x16,
    output reg signed [31:0] residual_x16,
    output reg signed [31:0] error_x16,
    output reg signed [31:0] delta_x16,
    output reg signed [31:0] bias_after_x16,
    output reg signed [31:0] fused_raw_x16,
    output reg signed [31:0] fused_pm25_x16,
    output reg [2:0] alert_level,
    output reg alert_state_before,
    output reg alert_state_after,
    output reg signed [31:0] bias_state_x16
);

reg alert_state;

wire accepted_next;
wire signed [31:0] residual_next_x16;
wire signed [31:0] error_next_x16;
wire signed [31:0] delta_next_x16;
wire signed [31:0] bias_after_next_x16;
wire signed [31:0] fused_raw_next_x16;
wire signed [31:0] fused_pm25_next_x16;
wire [2:0] alert_level_next;
wire alert_state_after_next;

assign sample_ready = 1'b1;

fusion u_fusion (
    .cams_pm25_x16(cams_pm25_x16),
    .bias_before_x16(bias_state_x16),
    .fused_raw_x16(fused_raw_next_x16),
    .fused_pm25_x16(fused_pm25_next_x16)
);

alert_classifier u_alert_classifier (
    .fused_pm25_x16(fused_pm25_next_x16),
    .alert_level(alert_level_next)
);

hysteresis u_hysteresis (
    .prev_alert_state(alert_state),
    .sample_valid(sample_valid),
    .fused_pm25_x16(fused_pm25_next_x16),
    .next_alert_state(alert_state_after_next)
);

bias_update #(
    .ALPHA_SHIFT(ALPHA_SHIFT)
) u_bias_update (
    .sample_valid(sample_valid),
    .qc_ok(qc_ok),
    .cams_pm25_x16(cams_pm25_x16),
    .pa_pm25_x16(pa_pm25_x16),
    .bias_before_x16(bias_state_x16),
    .accepted(accepted_next),
    .residual_x16(residual_next_x16),
    .error_x16(error_next_x16),
    .delta_x16(delta_next_x16),
    .bias_after_x16(bias_after_next_x16)
);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        bias_state_x16 <= 32'sd0;
        alert_state <= 1'b0;
        result_valid <= 1'b0;
        accepted <= 1'b0;
        hour_out <= 5'd0;
        bias_before_x16 <= 32'sd0;
        residual_x16 <= 32'sd0;
        error_x16 <= 32'sd0;
        delta_x16 <= 32'sd0;
        bias_after_x16 <= 32'sd0;
        fused_raw_x16 <= 32'sd0;
        fused_pm25_x16 <= 32'sd0;
        alert_level <= 3'd0;
        alert_state_before <= 1'b0;
        alert_state_after <= 1'b0;
    end else begin
        result_valid <= sample_valid;
        accepted <= accepted_next;
        hour_out <= hour;
        bias_before_x16 <= bias_state_x16;
        residual_x16 <= residual_next_x16;
        error_x16 <= error_next_x16;
        delta_x16 <= delta_next_x16;
        bias_after_x16 <= bias_after_next_x16;
        fused_raw_x16 <= fused_raw_next_x16;
        fused_pm25_x16 <= fused_pm25_next_x16;
        alert_level <= alert_level_next;
        alert_state_before <= alert_state;
        alert_state_after <= alert_state_after_next;
        bias_state_x16 <= bias_after_next_x16;
        alert_state <= alert_state_after_next;
    end
end

endmodule
