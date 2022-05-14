#include "mbed.h"
#include "max30100.h"
#include "functions.h"
#include "math.h"
#include "filter.h"

#define SIXTEENBIT 65535
#define True 1
#define False 0
#define mva_size 25
#define zero_pass_size 3
#define lzp 12
#define sample_rate 100

DigitalOut red_led(PA_0);

Serial pc(PA_2, PA_3); // tx, rx

MAX30100 hr_sensor;

double mwa_buffer[mva_size] = {0};
int lzpasses[lzp] = {0};
double zero_pass_buffer[zero_pass_size] = {0};


double moving_avg(double new_datapoint){
    
    for(int i = 0;i < mva_size - 1;i++){
        mwa_buffer[i] = mwa_buffer[i+1];
    }
    
    mwa_buffer[mva_size - 1] = new_datapoint;
    
    double mva_sum = 0;
    
    for(int i = 0;i<mva_size;i++){
        mva_sum += mwa_buffer[i];
    }
    
    return mva_sum / mva_size;
}


int check_zero_pass(double new_datapoint){
    for(int i = 0;i<zero_pass_size - 1;i++){
        zero_pass_buffer[i] = zero_pass_buffer[i+1];
    }
    
    zero_pass_buffer[zero_pass_size - 1] = new_datapoint;
    
    if(zero_pass_buffer[0] < 0){
       if(zero_pass_buffer[2] > 0){

            return True;
        }
    }
    
    return False;
}


float calculate_hr(int new_zero_pass){
        
        for(int i = 0;i<lzp - 1;i++){
            lzpasses[i] = lzpasses[i+1];
        }

        lzpasses[lzp - 1] = new_zero_pass;
        
        int lzp_sum = 0;
    
        for(int i = 0;i<lzp;i++){
            lzp_sum += lzpasses[i];
        }
        
        float beat_interval = static_cast<float>(lzp_sum) / (lzp);
        float heart_rate = 60 * (sample_rate/beat_interval);
        
        if(heart_rate < 150){
            return heart_rate;
        }
        
        return 0.0;
    }

int main()
{
    pc.baud(115200);
    
    high_resolution lr = high;
    pulseWidth pw = pw1600;
    sampleRate sr = sr100;
    ledCurrent lc = i50;

    hr_sensor.init(pw, sr, lr, lc, lc);
    
    char data_write[1];
    data_write[0] = MAX30100_MODE_SPO2;
    i2c_write(MAX30100_ADDRESS, MAX30100_CONFIG, data_write, 1);
    
    hr_sensor.printRegisters();
    
    BWHighPass* bw_hp_1;
    
    bw_hp_1 = create_bw_high_pass_filter(2, sample_rate, 0.67);
    
    double hr_val;
    double hr_mva;
    float spo2_val;
    int last_sample = 0;
    float heart_rate;
    
    // signal that initialization is succesfully done
    red_led.write(1);
    wait(0.3);
    red_led.write(0);
    wait(0.3);
    red_led.write(1);
    wait(0.3);
    red_led.write(0);
    
    while(1) {
        hr_sensor.readSensor();
        
        hr_val =  static_cast<double>(hr_sensor.HR) / SIXTEENBIT;
        spo2_val = static_cast<float>(hr_sensor.SPO2) / SIXTEENBIT;
        
        hr_val = bw_high_pass(bw_hp_1, hr_val);
        
        hr_mva = moving_avg(hr_val);
        
        if((check_zero_pass(hr_mva) == True) && (last_sample > 5)){
            
            heart_rate = calculate_hr(last_sample);
            
            if(spo2_val > 0.5){
                pc.printf("hr %.2f \n", heart_rate);
                pc.printf("spo2 %.2f \n", spo2_val * 100);
            }
            
            last_sample = 0;
        }
        else{
            last_sample += 1;
        }
        
        red_led.write(0);
        wait(0.01);
        red_led.write(1);
    }
}
