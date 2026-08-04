// Combinational adaptive-bias update for pm25_core_v1_adaptive_bias_fixed.
// Computes residual/error diagnostics and the next learned-bias value.
module bias_update #(
    parameter integer ALPHA_SHIFT = 3
) (
    input sample_valid,
    input qc_ok,
    input signed [31:0] cams_pm25_x16,
    input signed [31:0] pa_pm25_x16,
    input signed [31:0] bias_before_x16,
    output reg accepted,
    output signed [31:0] residual_x16,
    output signed [31:0] error_x16,
    output reg signed [31:0] delta_x16,
    output reg signed [31:0] bias_after_x16
);

`include "pm25_constants.vh"

wire signed [31:0] residual_calc_x16;
wire signed [31:0] error_calc_x16;
wire signed [31:0] delta_calc_x16;
wire signed [32:0] bias_sum_x16_ext;
wire signed [32:0] bias_min_x16_ext;
wire signed [32:0] bias_max_x16_ext;

assign residual_calc_x16 = pa_pm25_x16 - cams_pm25_x16;
assign error_calc_x16 = residual_calc_x16 - bias_before_x16;
assign delta_calc_x16 = error_calc_x16 >>> ALPHA_SHIFT;
assign bias_sum_x16_ext = {bias_before_x16[31], bias_before_x16}
                         + {delta_calc_x16[31], delta_calc_x16};
assign bias_min_x16_ext = {BIAS_MIN_X16[31], BIAS_MIN_X16};
assign bias_max_x16_ext = {BIAS_MAX_X16[31], BIAS_MAX_X16};

assign residual_x16 = residual_calc_x16;
assign error_x16 = error_calc_x16;

always @* begin
    accepted = 1'b0;
    delta_x16 = 32'sd0;
    bias_after_x16 = bias_before_x16;

    if (sample_valid && qc_ok) begin
        accepted = 1'b1;
        delta_x16 = delta_calc_x16;

        if (bias_sum_x16_ext < bias_min_x16_ext) begin
            bias_after_x16 = BIAS_MIN_X16;
        end else if (bias_sum_x16_ext > bias_max_x16_ext) begin
            bias_after_x16 = BIAS_MAX_X16;
        end else begin
            bias_after_x16 = bias_sum_x16_ext[31:0];
        end
    end
end

endmodule
