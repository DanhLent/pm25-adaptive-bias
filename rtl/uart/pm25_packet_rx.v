// Decode laptop-to-FPGA PM2.5 binary packets from received UART bytes.
module pm25_packet_rx (
    clk,
    rst_n,
    rx_valid,
    rx_byte,
    sample_valid_out,
    qc_ok_out,
    hour_out,
    cams_pm25_x16_out,
    pa_pm25_x16_out,
    packet_valid,
    checksum_error
);

input clk;
input rst_n;
input rx_valid;
input [7:0] rx_byte;
output reg sample_valid_out;
output reg qc_ok_out;
output reg [4:0] hour_out;
output reg signed [31:0] cams_pm25_x16_out;
output reg signed [31:0] pa_pm25_x16_out;
output reg packet_valid;
output reg checksum_error;

localparam [7:0] START_BYTE = 8'hA5;
localparam [0:0] STATE_WAIT_START = 1'd0;
localparam [0:0] STATE_COLLECT = 1'd1;

reg state;
reg [3:0] byte_index;
reg [7:0] checksum_sum;
reg [7:0] sample_valid_byte;
reg [7:0] qc_ok_byte;
reg [7:0] hour_byte;
reg [7:0] cams_hi;
reg [7:0] cams_lo;
reg [7:0] pa_hi;
reg [7:0] pa_lo;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= STATE_WAIT_START;
        byte_index <= 4'd0;
        checksum_sum <= 8'd0;
        sample_valid_byte <= 8'd0;
        qc_ok_byte <= 8'd0;
        hour_byte <= 8'd0;
        cams_hi <= 8'd0;
        cams_lo <= 8'd0;
        pa_hi <= 8'd0;
        pa_lo <= 8'd0;
        sample_valid_out <= 1'b0;
        qc_ok_out <= 1'b0;
        hour_out <= 5'd0;
        cams_pm25_x16_out <= 32'sd0;
        pa_pm25_x16_out <= 32'sd0;
        packet_valid <= 1'b0;
        checksum_error <= 1'b0;
    end else begin
        packet_valid <= 1'b0;
        checksum_error <= 1'b0;

        if (rx_valid) begin
            case (state)
                STATE_WAIT_START: begin
                    if (rx_byte == START_BYTE) begin
                        checksum_sum <= START_BYTE;
                        byte_index <= 4'd1;
                        state <= STATE_COLLECT;
                    end
                end

                STATE_COLLECT: begin
                    case (byte_index)
                        4'd1: begin
                            sample_valid_byte <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd2;
                        end
                        4'd2: begin
                            qc_ok_byte <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd3;
                        end
                        4'd3: begin
                            hour_byte <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd4;
                        end
                        4'd4: begin
                            cams_hi <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd5;
                        end
                        4'd5: begin
                            cams_lo <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd6;
                        end
                        4'd6: begin
                            pa_hi <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd7;
                        end
                        4'd7: begin
                            pa_lo <= rx_byte;
                            checksum_sum <= checksum_sum + rx_byte;
                            byte_index <= 4'd8;
                        end
                        4'd8: begin
                            state <= STATE_WAIT_START;
                            byte_index <= 4'd0;
                            if (rx_byte == checksum_sum) begin
                                sample_valid_out <= sample_valid_byte[0];
                                qc_ok_out <= qc_ok_byte[0];
                                if (hour_byte > 8'd23) begin
                                    hour_out <= 5'd23;
                                end else begin
                                    hour_out <= hour_byte[4:0];
                                end
                                cams_pm25_x16_out <= {{16{cams_hi[7]}}, cams_hi, cams_lo};
                                pa_pm25_x16_out <= {{16{pa_hi[7]}}, pa_hi, pa_lo};
                                packet_valid <= 1'b1;
                            end else begin
                                checksum_error <= 1'b1;
                            end
                        end
                        default: begin
                            state <= STATE_WAIT_START;
                            byte_index <= 4'd0;
                        end
                    endcase
                end

                default: begin
                    state <= STATE_WAIT_START;
                    byte_index <= 4'd0;
                end
            endcase
        end
    end
end

endmodule
