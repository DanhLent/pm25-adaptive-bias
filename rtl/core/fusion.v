// Combinational fused-output path for pm25_core_v1_adaptive_bias_fixed.
// Uses the pre-update learned bias and clamps the fused PM2.5 output.
module fusion (
    input signed [31:0] cams_pm25_x16,
    input signed [31:0] bias_before_x16,
    output signed [31:0] fused_raw_x16,
    output reg signed [31:0] fused_pm25_x16
);

`include "pm25_constants.vh"

wire signed [32:0] fused_raw_x16_ext;
wire signed [32:0] pm25_min_x16_ext;
wire signed [32:0] pm25_max_x16_ext;

assign fused_raw_x16_ext = {cams_pm25_x16[31], cams_pm25_x16}
                         + {bias_before_x16[31], bias_before_x16};
assign pm25_min_x16_ext = {PM25_MIN_X16[31], PM25_MIN_X16};
assign pm25_max_x16_ext = {PM25_MAX_X16[31], PM25_MAX_X16};
assign fused_raw_x16 = fused_raw_x16_ext[31:0];

always @* begin
    if (fused_raw_x16_ext < pm25_min_x16_ext) begin
        fused_pm25_x16 = PM25_MIN_X16;
    end else if (fused_raw_x16_ext > pm25_max_x16_ext) begin
        fused_pm25_x16 = PM25_MAX_X16;
    end else begin
        fused_pm25_x16 = fused_raw_x16_ext[31:0];
    end
end

endmodule
