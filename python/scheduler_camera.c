/* scheduler_camera.c

   routines to allow scheduler to open a socket connection
   to the camera controller (neatsrv on quest17), send
   commands and read replies

*/

#include "scheduler.h"

#define MACHINE_NAME "quest16_local"
#define COMMAND_PORT 3913  


#define COMMAND_DELAY_USEC 100000 /* useconds to wait between commands */

/* first word in reply from telescope controller */
#define ERROR_REPLY "-1"


/* Telescope Commands */

#define INIT_COMMAND "init"
#define OPEN_COMMAND "open shutter"
#define CLOSE_COMMAND "close shutter"
#define STATUS_COMMAND "status"
#define CLEAR_COMMAND "clear"
#define SHUTDOWN_COMMAND "shutdown"
#define READOUT_COMMAND "r" /* r num_lines fileroot */
#define HEADER_COMMAND "h" /* h keyword value */
#define EXPOSE_COMMAND "e" /* shutter exptime fileroot */

/* Timeout after 10 seconds if expecting quick response from
   a camera command */

#define CAMERA_TIMEOUT_SEC 10

/* call to status command is used to wait for readout.
   Readout time is normally 33 sec. Timeout after 3 minutes */

#define CAMERA_STATUS_TIMEOUT_SEC 180
#define CAMERA_CLEAR_TIMEOUT_SEC 120
#define CAMERA_INIT_TIMEOUT_SEC 60 

/* error code or readtime exceeding these two values,
   respectively, indicate bad readout of camera */

#define BAD_ERROR_CODE 2
#define BAD_READOUT_TIME 60.0



extern int verbose;
extern int verbose1;

/*****************************************************/

int take_exposure(Field *f, Fits_Header *header, double *actual_expt,
		    char *name, double *ut, double *jd)
{
    char command[MAXBUFSIZE],reply[MAXBUFSIZE];
    char filename[1024],date_string[1024],shutter_string[256],field_description[1024];
    char comment_line[1024];
    char s[256],code_string[1024],ujd_string[256],string[1024];
    struct tm tm;
    int e;
    double expt;
    int shutter;
    int timeout;

    if(*actual_expt!=0.0){
         expt=*actual_expt*3600.0;
    }
    else {
         expt=f->expt*3600.0;
    }

#if 0
    *actual_expt=0.0;
    expt=f->expt*3600.0;
#endif
    strcpy(name,"BAD");

    shutter = f->shutter;
    *ut=get_tm(&tm);
    *jd=get_jd();

    sprintf(ujd_string,"%14.6f",*jd);

    get_shutter_string(shutter_string,f->shutter,field_description);

    sprintf(date_string,"%04d%02d%02d %02d:%02d:%02d",
	tm.tm_year,tm.tm_mon,tm.tm_mday,tm.tm_hour,tm.tm_min,tm.tm_sec);

    get_filename(filename,&tm,shutter);
/*
    if(shutter){
        sprintf(filename,"%04d%02d%02d%02d%02d%02ds",
    	    tm.tm_year,tm.tm_mon,tm.tm_mday,tm.tm_hour,tm.tm_min,tm.tm_sec);
    }
    else{
        sprintf(filename,"%04d%02d%02d%02d%02d%02dd",
    	    tm.tm_year,tm.tm_mon,tm.tm_mday,tm.tm_hour,tm.tm_min,tm.tm_sec);
    }
*/
    if(verbose){
         fprintf(stderr,
           "take_exposure: exposing %7.1f sec  shutter: %d filename: %s\n",
           expt,shutter,filename);
         fflush(stderr);
    }

    sprintf(string,"%d",f->n_done+1);

    if(update_fits_header(header,SEQUENCE_KEYWORD,string)<0){
          fprintf(stderr,"take_exposure: error updating fits header %s:%s\n",
		SEQUENCE_KEYWORD,string);
          return(-1);
    }
    else if(update_fits_header(header,IMAGETYPE_KEYWORD,field_description)<0){
          fprintf(stderr,"take_exposure: error updating fits header %s:%s\n",
		IMAGETYPE_KEYWORD,field_description);
          return(-1);
    }
    else if(update_fits_header(header,FLATFILE_KEYWORD,filename)<0){
          fprintf(stderr,"take_exposure: error updating fits header %s:%s\n",
		FLATFILE_KEYWORD,filename);
       return(-1);
    }
/*
    else if(update_fits_header(header,UJD_KEYWORD,ujd_string)<0){
          fprintf(stderr,"take_exposure: error updating fits header %s:%s\n",
		UJD_KEYWORD,ujd_string);
       return(-1);
    }
*/
    /* if field is a sky field and there is a comment, then the strinf following
       the # sign should be the field id. Put this id string in the fieldid
       keyword of the fits header
    */

/*
    if(f->shutter==SKY_CODE&&strstr(f->script_line,"#")!=NULL){
       *code_string=0;
       sscanf(strstr(f->script_line,"#"),"%s %s",s,code_string);
       if(code_string!=0&&update_fits_header(header,FIELDID_KEYWORD,code_string)<0){
          fprintf(stderr,"take_exposure: error updating fits header %s:%s\n",
		FIELDID_KEYWORD,code_string);
          return(-1);
       }
    }
*/
    /* update comment line in FITS header with comments from script record */

    if(strstr(f->script_line,"#")!=NULL){
        sprintf(comment_line,"                      ");
        sprintf(comment_line,"'%s",strstr(f->script_line,"#")+1);
        strcpy(comment_line+strlen(comment_line)-1,"'");
    }
    else{
        sprintf(comment_line,"                      ");
        sprintf(comment_line,"'no comment'");
    }
    if(update_fits_header(header,COMMENT_KEYWORD,comment_line)<0){
          fprintf(stderr,"take_exposure: error updating fits header %s:%s\n",
		COMMENT_KEYWORD,comment_line);
       return(-1);
    }

    if(verbose){
      fprintf(stderr,"take_exposure: imprinting fits header\n");
      fflush(stderr);
    }

    if(imprint_fits_header(header)!=0){
      fprintf(stderr,"take_exposure: could not imprint fits header\n");
      return(-1);
    }

    sprintf(command,"e %d %9.3f %s",shutter,expt,filename);

    if(verbose){
        fprintf(stderr,"take_exposure: %s sending command %s\n",date_string,command);
    }

    timeout = 2*expt + 30 ;
    if(do_camera_command(command,reply,timeout)!=0){
       fprintf(stderr,"take_exposure: error sending exposure command : %s\n",command);
       fprintf(stderr,"take_exposure: reply was : %s\n",reply);
       *actual_expt=0.0;
       return(-1);
    }
    else{
       sscanf(reply,"%lf",actual_expt);
    }
    strncpy(name,filename,FILENAME_LENGTH);
/* DEBUG DLR 
    fprintf(stderr,"take_exposure: waiting extra 3 seconds for shutter to close\n");
    sleep (3);
*/

    if(verbose){
       fprintf(stderr,
           "take_exposure: exposure complete : filename %s  ut: %9.6f\n",
           filename,*ut);
       fflush(stderr);
    }

    
    return(0);
}

/*****************************************************/

int get_filename(char *filename,struct tm *tm,int shutter)
{
    char shutter_string[3];
    int result;
    char field_description[1024];

    result=get_shutter_string(shutter_string,shutter,field_description);
    if(result!=0){
        fprintf(stderr,"get_filename: bad shutter code: %d\n",shutter);
        fflush(stderr);
    }

    sprintf(filename,"%04d%02d%02d%02d%02d%02d%s",
            tm->tm_year,tm->tm_mon,tm->tm_mday,
	    tm->tm_hour,tm->tm_min,tm->tm_sec,shutter_string);

    return(result);
}

/*****************************************************/

int imprint_fits_header(Fits_Header *header)
{
    char command[MAXBUFSIZE];
    char reply[MAXBUFSIZE];
    int i;

    for(i=0;i<header->num_words;i++){
      sprintf(command,"%s %s %s",
		HEADER_COMMAND,header->fits_word[i].keyword,
                header->fits_word[i].value);
      if(do_camera_command(command,reply,CAMERA_TIMEOUT_SEC)!=0){
        fprintf(stderr,
          "imprint_fits_header: error sending command %s\n",command);
        return(-1);
      }
    }

    return(0);
}
     
/*****************************************************/

/* wait for camera to return status. This will not occur until
   readout of previous exposure completes */


int wait_camera_readout(Camera_Status *cam_status)
{
    struct timeval t1,t2;

    if(verbose){
         fprintf(stderr,"wait_camera_readout: waiting for camera status\n");
         fflush(stderr);
    }

    gettimeofday(&t1,NULL);
    if(update_camera_status(cam_status)!=0){
        fprintf(stderr,"wait_camera_readout: could not update camera status\n");
        return(-1);
    }
    gettimeofday(&t2,NULL);

    if(verbose){
         fprintf(stderr,
           "wait_camera_readout: done waiting for camera in %d sec\n",
            t2.tv_sec-t1.tv_sec);
         print_camera_status(cam_status,stderr);
         fflush(stderr);
    }


    if(bad_readout(cam_status)){
        fprintf(stderr,
             "wait_camera_readout: bad readout \n");
        fflush(stderr);
        return(-1);
    }
    else{
       return(0);
    }
}

/*****************************************************/

int init_camera()
{
     char reply[MAXBUFSIZE];
     char s[256],*s_ptr;


     if(do_camera_command(INIT_COMMAND,reply,CAMERA_INIT_TIMEOUT_SEC)!=0){
       return(-1);
     }
     else {
       return(0);
     }

     return(0);

}

/*****************************************************/

int clear_camera()
{
     char reply[MAXBUFSIZE];
     char s[256],*s_ptr;


     if(do_camera_command(CLEAR_COMMAND,reply,CAMERA_CLEAR_TIMEOUT_SEC)!=0){
       return(-1);
     }
     else {
       return(0);
     }

     return(0);

}

/*****************************************************/

int update_camera_status(Camera_Status *status)
{
     char reply[MAXBUFSIZE];
     int error_flag;
     char s[256],*s_ptr;

     error_flag=0;

     if(do_camera_command(STATUS_COMMAND,reply,CAMERA_STATUS_TIMEOUT_SEC)!=0){
       return(-1);
     }
     else {
       sscanf(reply,"%d %d %s %s %lf %d",
          &(status->line_count),
          &(status->write_lag),
          status->shutter_state,
          status->camera_mode,
          &(status->read_time),
          &(status->error_code));
     }


     return(0);

}
/*****************************************************/

int print_camera_status(Camera_Status *status,FILE *output)
{

   fprintf(output,"linecount    : %d\n",status->line_count);  
   fprintf(output,"writelag     : %d\n",status->write_lag);  
   fprintf(output,"shutter state: %s\n",status->shutter_state);  
   fprintf(output,"camera mode  : %s\n",status->camera_mode); 
   fprintf(output,"readout time : %7.3f\n",status->read_time); 
   fprintf(output,"error code   : %d\n",status->error_code); 
 
   return(0);
}

/*****************************************************/

int do_camera_command(char *command, char *reply, int timeout_sec)
{
     if(verbose1){
          fprintf(stderr,"do_camera_command: sending command %s\n",command);
          fflush(stderr);
     }

     if(send_command(command,reply,MACHINE_NAME,COMMAND_PORT, timeout_sec)!=0){
       fprintf(stderr,
          "do_camera_command: error sending commandt %s\n", command);
       return(-1);
     }
      
     usleep(COMMAND_DELAY_USEC);
     if(strstr(reply,ERROR_REPLY)!=NULL || strlen(reply) == 0 ){
       fprintf(stderr,
          "do_camera_command: error reading domestatus : %s\n", 
           reply);
       return(-1);
     }
     else {
       if(verbose1){
         fprintf(stderr,"do_camera_command: reply was %s\n",reply);
         fflush(stderr);
       }
       return(0);
     }
}

/*****************************************************/

int bad_readout(Camera_Status *status)
{
    if(status->error_code>BAD_ERROR_CODE){
      fprintf(stderr,"bad_readout: bad error code %s\n",status->error_code);
      return(1);
    }
    else if (status->read_time>=BAD_READOUT_TIME){
      fprintf(stderr,"bad_readout: long readout time : %7.3f\n",
            status->read_time);
      return(1);
    }

    return(0);
}

/*****************************************************/

